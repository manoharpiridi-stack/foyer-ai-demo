// Recent questions are kept in this browser only (localStorage): no backend, no database, nothing shared between visitors.
const MAX_ITEMS = 10;

export function loadHistory(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || [];
  } catch {
    return [];
  }
}

export function addToHistory(key, items, entry) {
  const next = [entry, ...items.filter((item) => item.question !== entry.question)].slice(0, MAX_ITEMS);
  try {
    localStorage.setItem(key, JSON.stringify(next));
  } catch {
    // Storage full or blocked (private window): the list still works for this visit.
  }
  return next;
}

export function clearHistory(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing to do.
  }
  return [];
}
