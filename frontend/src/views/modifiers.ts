type Values = Record<string, unknown>;
type Domain = unknown;

function actual(value: unknown): unknown {
  return Array.isArray(value) && value.length === 2 && typeof value[0] === "number" ? value[0] : value;
}

function condition(term: unknown[], values: Values): boolean {
  const [name, operator, expected] = term;
  const value = actual(values[String(name)]);
  switch (operator) {
    case "=": return value === expected || (!value && !expected);
    case "!=": return value !== expected && !(!value && !expected);
    case "in": return Array.isArray(expected) && expected.includes(value);
    case "not in": return Array.isArray(expected) && !expected.includes(value);
    case ">": return Number(value) > Number(expected);
    case ">=": return Number(value) >= Number(expected);
    case "<": return Number(value) < Number(expected);
    case "<=": return Number(value) <= Number(expected);
    case "like": return String(value ?? "").includes(String(expected ?? ""));
    case "ilike": return String(value ?? "").toLowerCase().includes(String(expected ?? "").toLowerCase());
    case "not like": return !String(value ?? "").includes(String(expected ?? ""));
    case "not ilike": return !String(value ?? "").toLowerCase().includes(String(expected ?? "").toLowerCase());
    case "set": return Boolean(value);
    case "not set": return !value;
    default: return false;
  }
}

export function evaluateDomain(domain: Domain, values: Values): boolean {
  if (typeof domain === "boolean") return domain;
  if (!Array.isArray(domain) || domain.length === 0) return false;
  if (domain.length >= 3 && typeof domain[0] === "string" && !["|", "&", "!"].includes(domain[0])) return condition(domain, values);

  let cursor = 0;
  const parse = (): boolean => {
    const token = domain[cursor++];
    if (token === "|") { const left = parse(); const right = parse(); return left || right; }
    if (token === "&") { const left = parse(); const right = parse(); return left && right; }
    if (token === "!") return !parse();
    return evaluateDomain(token, values);
  };
  let result = parse();
  while (cursor < domain.length) { const next = parse(); result = result && next; }
  return result;
}

export function modifierActive(modifiers: Record<string, unknown> | undefined, name: string, values: Values): boolean {
  return evaluateDomain(modifiers?.[name], values);
}
