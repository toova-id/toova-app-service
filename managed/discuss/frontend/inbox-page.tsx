import { ArrowLeft, Check, CheckCheck, Clock3, FileText, Hash, Inbox, LoaderCircle, MessageCircle, Paperclip, Plus, Reply, Search, Send, Smile, UserRound, Volume2, VolumeX, X } from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { ClientActionProps } from "@toova/features/feature-registry";
import { api, apiMutation, apiUpload } from "@toova/lib/api";
import { watchRealtimePresence } from "@toova/lib/realtime";
import { useSession } from "@toova/app/session";
import { Button } from "@toova/components/ui/button";
import { Input } from "@toova/components/ui/input";
import { MultiSelect, type MultiSelectOption } from "@toova/components/ui/multi-select";
import { RadioGroup, RadioGroupItem } from "@toova/components/ui/radio-group";
import { Textarea } from "@toova/components/ui/textarea";
import { cn } from "@toova/lib/utils";

type Conversation = { id: number; name: string; type: string; unread: number; date?: string; preview?: string; author?: string; avatarUrl?: string; memberCount: number };
type Activity = { id: number; summary: string; record: string; deadline: string; state: "overdue" | "today" | "planned"; path?: string };
type Mention = { id: number; author: string; preview: string; record?: string; date: string; path?: string };
type Attachment = { id: number; name: string; mimetype?: string; size?: number; url?: string; previewUrl?: string; localUrl?: string };
type Reaction = { content: string; count: number; mine: boolean };
type ReplyData = { id: number; author: string; body: string };
type MessageStatus = "sending" | "sent" | "delivered" | "read" | "failed";
type Message = { id: number; requestId?: string; author: string; authorInitials: string; body: string; date: string; mine: boolean; status: MessageStatus; readCount?: number; reply?: ReplyData; reactions: Reaction[]; attachments: Attachment[]; localFiles?: File[]; error?: string };
type Thread = { channel: { id: number; name: string; type: string; avatarUrl?: string; memberCount: number; otherPartnerId?: number; presence?: string; onlineCount: number }; messages: Message[]; firstUnreadId?: number };
type Overview = { conversations: Conversation[]; activities: Activity[]; mentions: Mention[]; counts: { messages: number; activities: number; mentions: number; attention: number }; canManageChannels: boolean };
type PartnerOption = MultiSelectOption & { email?: string; avatarUrl?: string };

const EMOJIS = ["😀", "😂", "🥰", "😍", "😊", "🙏", "👍", "👏", "🎉", "❤️", "🔥", "✅", "🤔", "😢", "😮", "💯", "👀", "🙌", "🤝", "🚀"];
const REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🙏"];
const MAX_FILES = 10;
const MAX_FILE_SIZE = 25 * 1024 * 1024;
const plain = (html: string) => { const node = document.createElement("div"); node.innerHTML = html; return node.innerText || node.textContent || ""; };
const parsedDate = (value?: string) => value ? new Date(value.replace(" ", "T") + (value.includes("Z") ? "" : "Z")) : undefined;
const dateLabel = (value?: string) => parsedDate(value)?.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) || "";
const dayKey = (value?: string) => parsedDate(value)?.toLocaleDateString("sv-SE") || "";
const dayLabel = (value?: string) => { const date = parsedDate(value); if (!date) return ""; const today = new Date(); const yesterday = new Date(); yesterday.setDate(today.getDate() - 1); if (date.toDateString() === today.toDateString()) return "Hari ini"; if (date.toDateString() === yesterday.toDateString()) return "Kemarin"; return date.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }); };
const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
const fileSize = (value = 0) => value >= 1024 * 1024 ? `${(value / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(value / 1024))} KB`;
const presenceLabel = (status?: string) => status === "online" ? "Online" : status === "away" ? "Tidak aktif" : "Offline";
const normalizeMessage = (message: Message): Message => ({
  ...message,
  status: message.status || "sent",
  reactions: message.reactions || [],
  attachments: message.attachments || [],
});
const normalizeThread = (value: Thread): Thread => ({
  ...value,
  channel: { ...value.channel, onlineCount: value.channel.onlineCount || 0 },
  messages: (value.messages || []).map(normalizeMessage),
});
function Avatar({ name, url, channel = false, presence }: { name: string; url?: string; channel?: boolean; presence?: string }) { return <span className={cn("toova-inbox-avatar", presence && `presence-${presence}`)}>{url ? <img src={url} alt=""/> : channel ? <Hash/> : initials(name)}</span>; }
function Receipt({ status, readCount, group }: { status: MessageStatus; readCount?: number; group?: boolean }) {
  if (status === "sending") return <span className="toova-message-receipt"><Clock3/>Mengirim</span>;
  if (status === "failed") return <span className="toova-message-receipt failed">Gagal</span>;
  if (group && status === "read" && readCount) return <span className="toova-message-receipt read"><CheckCheck/>Dibaca {readCount}</span>;
  if (status === "read") return <span className="toova-message-receipt read"><CheckCheck/></span>;
  if (status === "delivered") return <span className="toova-message-receipt"><CheckCheck/></span>;
  return <span className="toova-message-receipt"><Check/></span>;
}

export default function InboxPage(_props: ClientActionProps) {
  const session = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialView = searchParams.get("view");
  const [data, setData] = useState<Overview>();
  const [view, setView] = useState<"inbox" | "mentions" | "activities">(initialView === "mentions" || initialView === "activities" ? initialView : "inbox");
  const [channelId, setChannelId] = useState<number>();
  const [thread, setThread] = useState<Thread>();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "unread" | "channels" | "direct">("all");
  const [body, setBody] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [reply, setReply] = useState<ReplyData>();
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [reactionFor, setReactionFor] = useState<number>();
  const [typing, setTyping] = useState<string[]>([]);
  const [sound, setSound] = useState(() => localStorage.getItem("toova.inbox.sound") !== "false");
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
  const fileRef = useRef<HTMLInputElement>(null);
  const typingSent = useRef(false);
  const typingTimer = useRef<number>();
  const incomingTypingTimers = useRef(new Map<number, number>());
  const tempId = useRef(0);
  const applyOverview = (overview: Overview) => { setData(overview); window.dispatchEvent(new CustomEvent("toova:inbox-counts", { detail: overview.counts })); };
  const refresh = () => api<Overview>("/api/v1/inbox").then(applyOverview).catch((reason) => setError(reason.message));
  const loadThread = (id: number) => api<Thread>(`/api/v1/inbox/channels/${id}`).then((response) => { const result = normalizeThread(response); setThread(result); watchRealtimePresence(result.channel.otherPartnerId); return result; }).catch((reason) => { setError(reason.message); throw reason; });
  const loadPartners = (search = "") => api<{ items: { id: number; label: string; email?: string; avatarUrl?: string }[] }>(`/api/v1/inbox/partners?q=${encodeURIComponent(search)}`).then((result) => setPartners(result.items.map((item) => ({ value: item.id, label: item.label, email: item.email, avatarUrl: item.avatarUrl }))));
  const notifyTyping = (active: boolean) => { if (!channelId || typingSent.current === active) return; typingSent.current = active; apiMutation(`/api/v1/inbox/channels/${channelId}/typing`, "POST", { typing: active }).catch(() => undefined); };
  const markSeen = (current?: Thread, targetChannelId = channelId) => {
    const last = [...(current?.messages || [])].reverse().find((item) => item.id > 0);
    if (!targetChannelId || !last || document.visibilityState !== "visible") return;
    apiMutation(`/api/v1/inbox/channels/${targetChannelId}/seen`, "POST", { messageId: last.id }).then(refresh).catch(() => undefined);
  };

  useEffect(() => {
    const realtime = (event: Event) => {
      const notifications = (event as CustomEvent<{ type: string; payload: any }[]>).detail;
      if (!notifications.some((notification) => notification.type.startsWith("mail.") || notification.type.startsWith("bus."))) return;
      for (const notification of notifications.filter((item) => item.type === "mail.channel.member/typing_status")) {
        const payload = notification.payload || {};
        const partner = payload.persona?.partner;
        const targetChannel = payload.channel?.id;
        if (targetChannel !== channelId || !partner || partner.id === session.user.partnerId) continue;
        window.clearTimeout(incomingTypingTimers.current.get(partner.id));
        setTyping((items) => payload.isTyping ? [...new Set([...items, partner.name])] : items.filter((name) => name !== partner.name));
        if (payload.isTyping) incomingTypingTimers.current.set(partner.id, window.setTimeout(() => setTyping((items) => items.filter((name) => name !== partner.name)), 3500));
      }
      refresh();
      if (channelId && notifications.some((notification) => ["mail.channel/new_message", "mail.message/insert", "mail.channel.member/seen", "mail.channel.member/fetched", "bus.bus/im_status_updated", "bus/im_status"].includes(notification.type))) loadThread(channelId);
    };
    refresh();
    const timer = window.setInterval(refresh, 30000);
    const visible = () => { if (document.visibilityState === "visible") { refresh(); markSeen(thread); } };
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("toova:realtime", realtime);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", visible); window.removeEventListener("toova:realtime", realtime); };
  }, [channelId, thread?.messages.at(-1)?.id]);
  useEffect(() => { if (!channelId) return; setThread(undefined); setFiles([]); setReply(undefined); setTyping([]); loadThread(channelId).then((result) => { markSeen(result, channelId); refresh(); window.setTimeout(() => composerRef.current?.focus(), 0); }).catch(() => undefined); return () => notifyTyping(false); }, [channelId]);
  useEffect(() => { setSearchParams(view === "inbox" ? {} : { view }, { replace: true }); }, [view, setSearchParams]);
  useEffect(() => { const target = thread?.firstUnreadId ? document.getElementById(`inbox-unread-${thread.firstUnreadId}`) : undefined; if (target) target.scrollIntoView({ block: "center" }); else messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight }); markSeen(thread); }, [thread?.messages.at(-1)?.id]);
  useEffect(() => { if (compose || channelForm) loadPartners(); }, [compose, channelForm]);
  useEffect(() => { localStorage.setItem("toova.inbox.sound", String(sound)); window.dispatchEvent(new CustomEvent("toova:inbox-sound", { detail: sound })); }, [sound]);
  useEffect(() => { if (!composerRef.current) return; composerRef.current.style.height = "0px"; composerRef.current.style.height = `${Math.min(composerRef.current.scrollHeight, 128)}px`; }, [body]);
  const conversations = useMemo(() => (data?.conversations || []).filter((item) => `${item.name} ${item.preview || ""}`.toLowerCase().includes(query.toLowerCase())).filter((item) => filter === "all" || filter === "unread" && item.unread || filter === "channels" && item.type !== "chat" || filter === "direct" && item.type === "chat"), [data, query, filter]);

  const addFiles = (selected: FileList | File[]) => {
    const next = Array.from(selected);
    if (files.length + next.length > MAX_FILES) return setError("Maksimal 10 lampiran per pesan.");
    const tooLarge = next.find((file) => file.size > MAX_FILE_SIZE);
    if (tooLarge) return setError(`${tooLarge.name} melebihi 25 MB.`);
    setFiles((current) => [...current, ...next]);
  };
  const insertEmoji = (emoji: string) => {
    const input = composerRef.current;
    const start = input?.selectionStart ?? body.length;
    const end = input?.selectionEnd ?? body.length;
    setBody(`${body.slice(0, start)}${emoji}${body.slice(end)}`);
    setEmojiOpen(false);
    window.setTimeout(() => { input?.focus(); input?.setSelectionRange(start + emoji.length, start + emoji.length); }, 0);
  };
  const sendDraft = async (draft: Message) => {
    if (!channelId) return;
    try {
      const uploaded = await Promise.all((draft.localFiles || []).map((file) => apiUpload<{ attachment: Attachment }>(`/api/v1/inbox/channels/${channelId}/attachments`, file)));
      const result = await apiMutation<{ message: Message }>(`/api/v1/inbox/channels/${channelId}/messages`, "POST", {
        body: plain(draft.body), attachmentIds: uploaded.map((item) => item.attachment.id), parentId: draft.reply?.id, requestId: draft.requestId,
      });
      setThread((current) => current ? { ...current, messages: current.messages.map((item) => item.id === draft.id ? normalizeMessage(result.message) : item) } : current);
      refresh();
    } catch (reason) {
      setThread((current) => current ? { ...current, messages: current.messages.map((item) => item.id === draft.id ? { ...item, status: "failed", error: reason instanceof Error ? reason.message : String(reason) } : item) } : current);
    }
  };
  const send = () => {
    if (!channelId || (!body.trim() && !files.length)) return;
    notifyTyping(false);
    window.clearTimeout(typingTimer.current);
    const id = --tempId.current;
    const draft: Message = {
      id, requestId: crypto.randomUUID(), author: session.user.name, authorInitials: initials(session.user.name), body: body.trim(), date: new Date().toISOString(), mine: true,
      status: "sending", reactions: [], reply, localFiles: [...files], attachments: files.map((file, index) => ({ id: id * 100 - index, name: file.name, mimetype: file.type, size: file.size, localUrl: URL.createObjectURL(file) })),
    };
    setThread((current) => current ? { ...current, messages: [...current.messages, draft] } : current);
    setBody(""); setFiles([]); setReply(undefined); setEmojiOpen(false);
    sendDraft(draft);
  };
  const discardFailed = (message: Message) => {
    setThread((current) => current ? { ...current, messages: current.messages.filter((item) => item.id !== message.id) } : current);
  };
  const react = async (messageId: number, content: string) => {
    if (!channelId || messageId < 0) return;
    setReactionFor(undefined);
    const result = await apiMutation<{ message: Message }>(`/api/v1/inbox/channels/${channelId}/messages/${messageId}/reaction`, "POST", { content });
    setThread((current) => current ? { ...current, messages: current.messages.map((message) => message.id === messageId ? normalizeMessage(result.message) : message) } : current);
  };
  const startDirect = async (partnerId: string | number) => { const result = await apiMutation<{ channelId: number }>("/api/v1/inbox/direct", "POST", { partnerId }); setCompose(false); setChannelId(result.channelId); setView("inbox"); };
  const createChannel = async () => { if (!channelName.trim()) return; const result = await apiMutation<{ channelId: number }>("/api/v1/inbox/channels", "POST", { name: channelName, visibility, partnerIds: members.map((item) => Number(item.value)) }); setChannelForm(false); setChannelName(""); setMembers([]); await refresh(); setChannelId(result.channelId); };
  const done = async (id: number) => { await apiMutation(`/api/v1/inbox/activities/${id}/done`, "POST", {}); refresh(); };
  const scrollToMessage = (id: number) => document.getElementById(`inbox-message-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });

  return <div className={cn("toova-inbox", channelId && "thread-open")}>
    <section className="toova-inbox-list">
      <header><div className="toova-inbox-list-title"><h1>Inbox</h1><div><Button variant="ghost" size="icon" onClick={() => setSound((value) => !value)} aria-label={sound ? "Matikan suara pesan" : "Aktifkan suara pesan"}>{sound ? <Volume2/> : <VolumeX/>}</Button><Button variant="ghost" size="icon" onClick={() => setCompose(true)} aria-label="Pesan baru"><Plus/></Button></div></div><div className="toova-inbox-tabs"><button className={view === "inbox" ? "active" : undefined} onClick={() => setView("inbox")}><Inbox/>Pesan{data?.counts.messages ? <b>{data.counts.messages}</b> : null}</button><button className={view === "mentions" ? "active" : undefined} onClick={() => { setView("mentions"); setChannelId(undefined); }}><MessageCircle/>Mention{data?.counts.mentions ? <b>{data.counts.mentions}</b> : null}</button><button className={view === "activities" ? "active" : undefined} onClick={() => { setView("activities"); setChannelId(undefined); }}><Check/>Aktivitas{data?.counts.activities ? <b>{data.counts.activities}</b> : null}</button></div><label><Search/><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari..."/></label></header>
      {view === "inbox" && <><div className="toova-inbox-filters">{[["all", "Semua"], ["unread", "Belum dibaca"], ["channels", "Channel"], ["direct", "Langsung"]].map(([key, label]) => <button key={key} className={filter === key ? "active" : undefined} onClick={() => setFilter(key as typeof filter)}>{label}</button>)}</div><div className="toova-inbox-conversations">{conversations.map((item) => <button key={item.id} className={channelId === item.id ? "active" : undefined} onClick={() => setChannelId(item.id)}><Avatar name={item.name} url={item.avatarUrl} channel={item.type !== "chat"}/><div><strong>{item.name}</strong><small>{item.preview ? `${item.type !== "chat" && item.author ? `${item.author}: ` : ""}${item.preview}` : ""}</small></div><time>{dateLabel(item.date)}</time>{item.unread > 0 && <b>{item.unread}</b>}</button>)}{!conversations.length && <div className="toova-inbox-empty">Tidak ada pesan</div>}</div></>}
      {view === "mentions" && <div className="toova-inbox-items">{data?.mentions.map((item) => <article key={item.id}><div><strong>{item.author}</strong><small>{item.record}</small></div><p>{item.preview}</p>{item.path && <Link to={item.path}>Buka</Link>}</article>)}{!data?.mentions.length && <div className="toova-inbox-empty">Tidak ada mention</div>}</div>}
      {view === "activities" && <div className="toova-inbox-items">{data?.activities.map((item) => <article key={item.id} className={item.state}><div><strong>{item.summary}</strong><small>{item.record}</small></div><time>{new Date(`${item.deadline}T00:00:00`).toLocaleDateString("id-ID")}</time><div>{item.path && <Link to={item.path}>Buka</Link>}<button onClick={() => done(item.id)}>Selesai</button></div></article>)}{!data?.activities.length && <div className="toova-inbox-empty">Tidak ada aktivitas</div>}</div>}
    </section>
    <main className="toova-inbox-thread">{thread ? <><header><button onClick={() => setChannelId(undefined)} aria-label="Kembali"><ArrowLeft/></button><Avatar name={thread.channel.name} url={thread.channel.avatarUrl} channel={thread.channel.type !== "chat"} presence={thread.channel.type === "chat" ? thread.channel.presence : undefined}/><div><h2>{thread.channel.name}</h2><small>{typing.length ? `${typing.slice(0, 2).join(", ")} sedang mengetik…` : thread.channel.type === "chat" ? presenceLabel(thread.channel.presence) : `${thread.channel.memberCount} anggota · ${thread.channel.onlineCount} online`}</small></div></header><div className="toova-inbox-messages" ref={messagesRef}>{thread.messages.map((message, index) => { const previous = thread.messages[index - 1]; const direct = thread.channel.type === "chat"; const grouped = Boolean(previous && previous.mine === message.mine && previous.author === message.author && dayKey(previous.date) === dayKey(message.date)); return <Fragment key={message.id}>{(!index || dayKey(previous?.date) !== dayKey(message.date)) && <div className="toova-inbox-day"><span>{dayLabel(message.date)}</span></div>}{thread.firstUnreadId === message.id && <div id={`inbox-unread-${message.id}`} className="toova-inbox-unread"><span>Pesan baru</span></div>}<article id={`inbox-message-${message.id}`} className={cn(message.mine && "mine", direct && "direct", grouped && "grouped", message.status === "failed" && "failed")} onMouseLeave={() => setReactionFor(undefined)}>{!message.mine && !direct && !grouped && <span>{message.authorInitials}</span>}<div>{!direct && !message.mine && !grouped && <header><strong>{message.author}</strong></header>}{message.reply && <button className="toova-message-reply-preview" onClick={() => scrollToMessage(message.reply!.id)}><strong>{message.reply.author}</strong><span>{message.reply.body || "Lampiran"}</span></button>}<p>{plain(message.body)}</p><div className="toova-message-attachments">{(message.attachments || []).map((attachment) => attachment.mimetype?.startsWith("image/") ? <a key={attachment.id} href={attachment.url || attachment.localUrl} target="_blank" rel="noreferrer"><img src={attachment.previewUrl || attachment.localUrl} alt={attachment.name}/><span>{attachment.name}</span></a> : <a key={attachment.id} href={attachment.url || attachment.localUrl} download={attachment.name}><FileText/><span><strong>{attachment.name}</strong><small>{fileSize(attachment.size)}</small></span></a>)}</div><div className="toova-message-meta"><time>{parsedDate(message.date)?.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}</time>{message.mine && <Receipt status={message.status || "sent"} readCount={message.readCount} group={!direct}/>}</div>{(message.reactions || []).length > 0 && <div className="toova-message-reactions">{(message.reactions || []).map((item) => <button key={item.content} className={item.mine ? "mine" : undefined} onClick={() => react(message.id, item.content)}>{item.content}<b>{item.count}</b></button>)}</div>}{message.status === "failed" && <div className="toova-message-failed-actions"><button className="toova-message-retry" onClick={() => { setThread((current) => current ? { ...current, messages: current.messages.map((item) => item.id === message.id ? { ...item, status: "sending" } : item) } : current); sendDraft({ ...message, status: "sending" }); }}>Coba lagi</button><button onClick={() => discardFailed(message)}>Hapus</button></div>}<div className="toova-message-actions"><button onClick={() => { setReply({ id: message.id, author: message.author, body: plain(message.body) || "Lampiran" }); composerRef.current?.focus(); }} aria-label="Balas"><Reply/></button><button onClick={() => setReactionFor(reactionFor === message.id ? undefined : message.id)} aria-label="Reaction"><Smile/></button>{reactionFor === message.id && <span>{REACTIONS.map((emoji) => <button key={emoji} onClick={() => react(message.id, emoji)}>{emoji}</button>)}</span>}</div></div></article></Fragment>; })}</div><footer className="toova-inbox-composer">{reply && <div className="toova-composer-reply"><Reply/><span><strong>Membalas {reply.author}</strong><small>{reply.body}</small></span><button onClick={() => setReply(undefined)} aria-label="Batal membalas"><X/></button></div>}{files.length > 0 && <div className="toova-composer-files">{files.map((file, index) => <span key={`${file.name}-${index}`}><FileText/><i><strong>{file.name}</strong><small>{fileSize(file.size)}</small></i><button onClick={() => setFiles((items) => items.filter((_, position) => position !== index))}><X/></button></span>)}</div>}<div className="toova-composer-row"><input ref={fileRef} type="file" multiple hidden onChange={(event) => { if (event.target.files) addFiles(event.target.files); event.target.value = ""; }}/><button type="button" aria-label="Lampiran" onClick={() => fileRef.current?.click()}><Paperclip/></button><div className="toova-composer-input"><Textarea ref={composerRef} rows={1} value={body} onPaste={(event) => { const pasted = Array.from(event.clipboardData.files); if (pasted.length) addFiles(pasted); }} onChange={(event) => { setBody(event.target.value); notifyTyping(true); window.clearTimeout(typingTimer.current); typingTimer.current = window.setTimeout(() => notifyTyping(false), 2200); }} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Tulis pesan"/><button type="button" aria-label="Emoji" onClick={() => setEmojiOpen((value) => !value)}><Smile/></button>{emojiOpen && <div className="toova-emoji-picker">{EMOJIS.map((emoji) => <button key={emoji} onClick={() => insertEmoji(emoji)}>{emoji}</button>)}</div>}</div><button type="button" className={cn("toova-composer-send", (!body.trim() && !files.length) && "opacity-40")} disabled={!body.trim() && !files.length} onClick={send}><Send/></button></div></footer></> : <div className="toova-inbox-empty"><MessageCircle/><span>Pilih percakapan</span></div>}</main>
    {compose && <div className="toova-inbox-drawer"><section><header><h2>Pesan baru</h2><button onClick={() => setCompose(false)}><X/></button></header><Input autoFocus value={composeQuery} onChange={(event) => { setComposeQuery(event.target.value); loadPartners(event.target.value); }} placeholder="Cari nama atau email"/><div>{partners.map((partner) => <button key={String(partner.value)} onClick={() => startDirect(partner.value)}><Avatar name={partner.label} url={partner.avatarUrl}/><span><strong>{partner.label}</strong><small>{partner.email}</small></span></button>)}</div>{data?.canManageChannels && <footer><button onClick={() => { setCompose(false); setChannelForm(true); }}><Hash/>Buat channel</button></footer>}</section></div>}
    {channelForm && <div className="toova-inbox-modal" onMouseDown={(event) => event.target === event.currentTarget && setChannelForm(false)}><section><header><h2>Channel baru</h2><button onClick={() => setChannelForm(false)}><X/></button></header><label><span>Nama</span><Input autoFocus value={channelName} onChange={(event) => setChannelName(event.target.value)}/></label><label><span>Akses</span><RadioGroup value={visibility} onValueChange={(value) => setVisibility(value as typeof visibility)}><label><RadioGroupItem value="private"/>Hanya anggota</label><label><RadioGroupItem value="public"/>Semua pengguna</label></RadioGroup></label>{visibility === "private" && <label><span>Anggota</span><MultiSelect options={partners} value={members} onSearch={loadPartners} onChange={(value) => setMembers(value as PartnerOption[])} placeholder="Pilih anggota"/></label>}<footer><Button variant="ghost" onClick={() => setChannelForm(false)}>Batal</Button><Button onClick={createChannel} disabled={!channelName.trim()}>Buat</Button></footer></section></div>}
    {error && <div className="workspace-toast-error" onClick={() => setError(undefined)}>{error}</div>}
  </div>;
}
