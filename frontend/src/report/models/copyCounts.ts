/** Words in the exact string that will be printed. */
export function countWords(text: string | null | undefined): number {
  const trimmed = (text || '').trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).filter(Boolean).length;
}
