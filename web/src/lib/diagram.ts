// Diagram specs as the web sees them. The engine draws every figure (POST /render/diagram,
// see ServerDiagram.svelte), so one renderer and one label-collision test cover what the
// editor, the Classic page and the PDF show (EXA-151). The web keeps only a raster figure's
// <img>: it is a picture carried verbatim, not a drawing.

/** The before-after bar model: the web reads its view_mode for the toggle-bar-view edit. */
export interface BarModelBeforeAfterSpec {
  type: 'bar_model_before_after'
  view_mode?: 'grouped' | 'sliced'
  [key: string]: unknown
}

/** A sourced/ingested figure carried verbatim as an image (asset_ref, usually a data: URI). */
export interface RasterSpec {
  type: 'raster'
  asset_ref: string
  alt_text?: string
}

/** Every other figure type: opaque to the client, drawn by the engine. */
export interface ServerSpec {
  type:
    | 'bar_model'
    | 'shaded_fraction'
    | 'geometry_figure'
    | 'chart'
    | 'solid'
    | 'number_line'
    | 'panels'
    | 'cube_stack'
    | 'net'
  [key: string]: unknown
}

export type DiagramSpec = ServerSpec | BarModelBeforeAfterSpec | RasterSpec
