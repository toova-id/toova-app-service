import { ArrowLeft, Check, Hash, Inbox, MessageCircle, Plus, Search, Send, UserRound, X } from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { ClientActionProps } from "@luma/features/feature-registry";
import { api, apiMutation } from "@luma/lib/api";
import { Button } from "@luma/components/ui/button";
import { Input } from "@luma/components/ui/input";
import { MultiSelect, type MultiSelectOption } from "@luma/components/ui/multi-select";
import { RadioGroup, RadioGroupItem } from "@luma/components/ui/radio-group";
import { Textarea } from "@luma/components/ui/textarea";
import { cn } from "@luma/lib/utils";

type Conversation = { id: number; name: string; type: string; unread: number; date?: string; preview?: string; author?: string; avatarUrl?: string; memberCount: number };
type Activity = { id: number; summary: string; record: string; deadline: string; state: "overdue" | "today" | "planned"; path?: string };
type Mention = { id: number; author: string; preview: string; record?: string; date: string; path?: string };
type Message = { id: number; author: string; authorInitials: string; body: string; date: string; mine: boolean; attachments: { id: number; name: string }[] };
type Thread = { channel: { id: number; name: string; type: string; avatarUrl?: string; memberCount: number }; messages: Message[]; firstUnreadId?: number };
type Overview = { conversations: Conversation[]; activities: Activity[]; mentions: Mention[]; counts: { messages: number; activities: number; mentions: number; attention: number }; canManageChannels: boolean };
type PartnerOption = MultiSelectOption & { email?: string; avatarUrl?: string };

const plain = (html: string) => { const node = document.createElement("div"); node.innerHTML = html; return node.innerText || node.textContent || ""; };
const parsedDate = (value?: string) => value ? new Date(value.replace(" ", "T") + (value.includes("Z") ? "" : "Z")) : undefined;
const dateLabel = (value?: string) => parsedDate(value)?.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) || "";
const dayKey = (value?: string) => parsedDate(value)?.toLocaleDateString("sv-SE") || "";
const dayLabel = (value?: string) => { const date = parsedDate(value); if (!date) return ""; const today = new Date(); const yesterday = new Date(); yesterday.setDate(today.getDate() - 1); if (date.toDateString() === today.toDateString()) return "Hari ini"; if (date.toDateString() === yesterday.toDateString()) return "Kemarin"; return date.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }); };
const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
function Avatar({ name, url, channel = false }: { name: string; url?: string; channel?: boolean }) { return <span className="luma-inbox-avatar">{url ? <img src={url} alt=""/> : channel ? <Hash/> : initials(name)}</span>; }

export default function InboxPage(_props: ClientActionProps) {
  const [data, setData] = useState<Overview>();
  const [view, setView] = useState<"inbox" | "mentions" | "activities">("inbox");
  const [channelId, setChannelId] = useState<number>();
  const [thread, setThread] = useState<Thread>();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "unread" | "channels" | "direct">("all");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [compose, setCompose] = useState(false);
  const [composeQuery, setComposeQuery] = useState("");
  const [partners, setPartners] = useState<PartnerOption[]>([]);
  const [channelForm, setChannelForm] = useState(false);
  const [channelName, setChannelName] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("private");
  const [members, setMembers] = useState<PartnerOption[]>([]);
  const [error, setError] = useState<string>();
  const messagesRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const refresh = () => api<Overview>("/api/v1/inbox").then(setData).catch((reason) => setError(reason.message));
  const loadPartners = (search = "") => api<{ items: { id: number; label: string; email?: string; avatarUrl?: string }[] }>(`/api/v1/inbox/partners?q=${encodeURIComponent(search)}`).then((result) => setPartners(result.items.map((item) => ({ value: item.id, label: item.label, email: item.email, avatarUrl: item.avatarUrl }))));
  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 30000); const visible = () => { if (document.visibilityState === "visible") refresh(); }; document.addEventListener("visibilitychange", visible); return () => { clearInterval(timer); document.removeEventListener("visibilitychange", visible); }; }, []);
  useEffect(() => { if (channelId) api<Thread>(`/api/v1/inbox/channels/${channelId}`).then((result) => { setThread(result); refresh(); window.setTimeout(() => composerRef.current?.focus(), 0); }).catch((reason) => setError(reason.message)); }, [channelId]);
  useEffect(() => { const target = thread?.firstUnreadId ? document.getElementById(`inbox-unread-${thread.firstUnreadId}`) : undefined; if (target) target.scrollIntoView({ block: "center" }); else messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight }); }, [thread]);
  useEffect(() => { if (compose || channelForm) loadPartners(); }, [compose, channelForm]);
  const conversations = useMemo(() => (data?.conversations || []).filter((item) => `${item.name} ${item.preview || ""}`.toLowerCase().includes(query.toLowerCase())).filter((item) => filter === "all" || filter === "unread" && item.unread || filter === "channels" && item.type !== "chat" || filter === "direct" && item.type === "chat"), [data, query, filter]);
  const send = async () => { if (!channelId || !body.trim()) return; setSending(true); try { const result = await apiMutation<{ message: Message }>(`/api/v1/inbox/channels/${channelId}/messages`, "POST", { body }); setThread((current) => current ? { ...current, messages: [...current.messages, result.message] } : current); setBody(""); refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } finally { setSending(false); } };
  const startDirect = async (partnerId: string | number) => { const result = await apiMutation<{ channelId: number }>("/api/v1/inbox/direct", "POST", { partnerId }); setCompose(false); setChannelId(result.channelId); setView("inbox"); };
  const createChannel = async () => { if (!channelName.trim()) return; const result = await apiMutation<{ channelId: number }>("/api/v1/inbox/channels", "POST", { name: channelName, visibility, partnerIds: members.map((item) => Number(item.value)) }); setChannelForm(false); setChannelName(""); setMembers([]); await refresh(); setChannelId(result.channelId); };
  const done = async (id: number) => { await apiMutation(`/api/v1/inbox/activities/${id}/done`, "POST", {}); refresh(); };
  return <div className={cn("luma-inbox", channelId && "thread-open")}>
    <section className="luma-inbox-list">
      <header><div className="luma-inbox-list-title"><h1>Inbox</h1><Button variant="ghost" size="icon" onClick={() => setCompose(true)} aria-label="Pesan baru"><Plus/></Button></div><div className="luma-inbox-tabs"><button className={view === "inbox" ? "active" : undefined} onClick={() => { setView("inbox"); }}><Inbox/>Pesan{data?.counts.messages ? <b>{data.counts.messages}</b> : null}</button><button className={view === "mentions" ? "active" : undefined} onClick={() => { setView("mentions"); setChannelId(undefined); }}><MessageCircle/>Mention{data?.counts.mentions ? <b>{data.counts.mentions}</b> : null}</button><button className={view === "activities" ? "active" : undefined} onClick={() => { setView("activities"); setChannelId(undefined); }}><Check/>Aktivitas{data?.counts.activities ? <b>{data.counts.activities}</b> : null}</button></div><label><Search/><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari..."/></label></header>
      {view === "inbox" && <><div className="luma-inbox-filters">{[["all", "Semua"], ["unread", "Belum dibaca"], ["channels", "Channel"], ["direct", "Langsung"]].map(([key, label]) => <button key={key} className={filter === key ? "active" : undefined} onClick={() => setFilter(key as typeof filter)}>{label}</button>)}</div><div className="luma-inbox-conversations">{conversations.map((item) => <button key={item.id} className={channelId === item.id ? "active" : undefined} onClick={() => setChannelId(item.id)}><Avatar name={item.name} url={item.avatarUrl} channel={item.type !== "chat"}/><div><strong>{item.name}</strong><small>{item.preview ? `${item.type !== "chat" && item.author ? `${item.author}: ` : ""}${item.preview}` : ""}</small></div><time>{dateLabel(item.date)}</time>{item.unread > 0 && <b>{item.unread}</b>}</button>)}{!conversations.length && <div className="luma-inbox-empty">Tidak ada pesan</div>}</div></>}
      {view === "mentions" && <div className="luma-inbox-items">{data?.mentions.map((item) => <article key={item.id}><div><strong>{item.author}</strong><small>{item.record}</small></div><p>{item.preview}</p>{item.path && <Link to={item.path}>Buka</Link>}</article>)}{!data?.mentions.length && <div className="luma-inbox-empty">Tidak ada mention</div>}</div>}
      {view === "activities" && <div className="luma-inbox-items">{data?.activities.map((item) => <article key={item.id} className={item.state}><div><strong>{item.summary}</strong><small>{item.record}</small></div><time>{new Date(`${item.deadline}T00:00:00`).toLocaleDateString("id-ID")}</time><div>{item.path && <Link to={item.path}>Buka</Link>}<button onClick={() => done(item.id)}>Selesai</button></div></article>)}{!data?.activities.length && <div className="luma-inbox-empty">Tidak ada aktivitas</div>}</div>}
    </section>
    <main className="luma-inbox-thread">{thread ? <><header><button onClick={() => setChannelId(undefined)} aria-label="Kembali"><ArrowLeft/></button><Avatar name={thread.channel.name} url={thread.channel.avatarUrl} channel={thread.channel.type !== "chat"}/><div><h2>{thread.channel.name}</h2>{thread.channel.type !== "chat" && <small>{thread.channel.memberCount} anggota</small>}</div></header><div className="luma-inbox-messages" ref={messagesRef}>{thread.messages.map((message, index) => { const previous = thread.messages[index - 1]; const direct = thread.channel.type === "chat"; const grouped = Boolean(previous && previous.mine === message.mine && previous.author === message.author && dayKey(previous.date) === dayKey(message.date)); return <Fragment key={message.id}>{(!index || dayKey(previous?.date) !== dayKey(message.date)) && <div className="luma-inbox-day"><span>{dayLabel(message.date)}</span></div>}{thread.firstUnreadId === message.id && <div id={`inbox-unread-${message.id}`} className="luma-inbox-unread"><span>Pesan baru</span></div>}<article className={cn(message.mine && "mine", direct && "direct", grouped && "grouped")}>{!message.mine && !direct && !grouped && <span>{message.authorInitials}</span>}<div>{!direct && !message.mine && !grouped && <header><strong>{message.author}</strong></header>}<p>{plain(message.body)}</p>{message.attachments.map((attachment) => <a key={attachment.id} href={`/mail/channel/${thread.channel.id}/attachment/${attachment.id}?download=1`}>{attachment.name}</a>)}<time>{parsedDate(message.date)?.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}</time></div></article></Fragment>; })}</div><footer><button type="button" aria-label="Lampiran" disabled><Plus/></button><Textarea ref={composerRef} value={body} onChange={(event) => setBody(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Pesan"/><Button onClick={send} disabled={sending || !body.trim()} size="icon"><Send/></Button></footer></> : <div className="luma-inbox-empty"><MessageCircle/><span>Pilih percakapan</span></div>}</main>
    {compose && <div className="luma-inbox-drawer"><section><header><h2>Pesan baru</h2><button onClick={() => setCompose(false)}><X/></button></header><Input autoFocus value={composeQuery} onChange={(event) => { setComposeQuery(event.target.value); loadPartners(event.target.value); }} placeholder="Cari nama atau email"/><div>{partners.map((partner) => <button key={String(partner.value)} onClick={() => startDirect(partner.value)}><Avatar name={partner.label} url={partner.avatarUrl}/><span><strong>{partner.label}</strong><small>{partner.email}</small></span></button>)}</div>{data?.canManageChannels && <footer><button onClick={() => { setCompose(false); setChannelForm(true); }}><Hash/>Buat channel</button></footer>}</section></div>}
    {channelForm && <div className="luma-inbox-modal" onMouseDown={(event) => event.target === event.currentTarget && setChannelForm(false)}><section><header><h2>Channel baru</h2><button onClick={() => setChannelForm(false)}><X/></button></header><label><span>Nama</span><Input autoFocus value={channelName} onChange={(event) => setChannelName(event.target.value)}/></label><label><span>Akses</span><RadioGroup value={visibility} onValueChange={(value) => setVisibility(value as typeof visibility)}><label><RadioGroupItem value="private"/>Hanya anggota</label><label><RadioGroupItem value="public"/>Semua pengguna</label></RadioGroup></label>{visibility === "private" && <label><span>Anggota</span><MultiSelect options={partners} value={members} onSearch={loadPartners} onChange={(value) => setMembers(value as PartnerOption[])} placeholder="Pilih anggota"/></label>}<footer><Button variant="ghost" onClick={() => setChannelForm(false)}>Batal</Button><Button onClick={createChannel} disabled={!channelName.trim()}>Buat</Button></footer></section></div>}
    {error && <div className="workspace-toast-error">{error}</div>}
  </div>;
}
