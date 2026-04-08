/**
 * Input validation helpers for Spotify API parameters.
 */

/** Validates a Spotify ID (playlist, track, album, artist). 22-char Base62 string. */
export function isValidSpotifyId(id: string): boolean {
  return /^[A-Za-z0-9]{22}$/.test(id);
}

type DiffOperation = "only_a" | "only_b" | "shared" | "union" | "difference";
const VALID_DIFF_OPERATIONS: DiffOperation[] = ["only_a", "only_b", "shared", "union", "difference"];

export function isValidDiffOperation(op: string): op is DiffOperation {
  return VALID_DIFF_OPERATIONS.includes(op as DiffOperation);
}

type SortField = "release_date" | "artist" | "date_added" | "album_name" | "popularity" | "track_name";
const VALID_SORT_FIELDS: SortField[] = ["release_date", "artist", "date_added", "album_name", "popularity", "track_name"];

export function isValidSortField(field: string): field is SortField {
  return VALID_SORT_FIELDS.includes(field as SortField);
}

export function validateArrayLength(arr: unknown[], maxLength: number, fieldName: string): string | null {
  if (!Array.isArray(arr)) return `${fieldName} must be an array`;
  if (arr.length > maxLength) return `${fieldName} must not exceed ${maxLength} items`;
  return null;
}
