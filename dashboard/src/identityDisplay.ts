/**
 * API может отдавать идентичность в виде `тип:значение`. В UI показываем только значение без префикса `email:`, `telegram:` и т.д.
 */
export function identityWithoutTypePrefix(raw: string): string {
  const idx = raw.indexOf(":");
  if (idx === -1) {
    return raw;
  }
  const rest = raw.slice(idx + 1).trim();
  return rest.length > 0 ? rest : raw;
}

export function identitiesWithoutTypePrefixes(rows: readonly string[]): string {
  return rows.map(identityWithoutTypePrefix).join(", ");
}
