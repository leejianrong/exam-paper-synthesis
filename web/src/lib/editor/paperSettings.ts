// The paper-wide print settings, shared with the question node views (which are mounted by
// ProseMirror, outside the page component's tree). EditorPage owns it; node views read it.
import { writable } from "svelte/store";
import { DEFAULT_PLACEMENT, type PaperSettings } from "./layout";

export const paperSettings = writable<PaperSettings>({
  marks_placement: DEFAULT_PLACEMENT,
});
