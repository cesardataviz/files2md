// Plantilla de PDF de files2md.
// El contenido NO se inserta como código Typst: llega como JSON en sys.inputs.doc y esta plantilla lo dibuja.
// Así un documento con caracteres especiales (#, *, $, //, <...>) no puede romper ni ejecutar nada.

#let data = json(bytes(sys.inputs.doc))

#set document(title: data.title)
#set page(paper: "a4", margin: (x: 2.3cm, y: 2.4cm), numbering: "1")
#set text(size: 10.5pt, lang: "es")
#set par(leading: 0.72em, spacing: 1.15em)
#show heading: set block(above: 1.5em, below: 0.8em)
#show heading.where(level: 1): set text(size: 19pt)
#show heading.where(level: 2): set text(size: 14.5pt)
#show raw.where(block: true): block.with(fill: luma(245), inset: 9pt, radius: 4pt, width: 100%)

#let runs(rs) = {
  for r in rs {
    let c = if r.code { raw(r.text) } else { r.text }
    if r.bold { c = strong(c) }
    if r.italic { c = emph(c) }
    c
  }
}

#let render(b) = {
  if b.type == "heading" {
    heading(level: calc.min(b.level, 6), runs(b.runs))
  } else if b.type == "paragraph" {
    par(runs(b.runs))
  } else if b.type == "list" {
    let items = b.items.map(it => {
      runs(it.runs)
      for child in it.children { render(child) }
    })
    if b.ordered { enum(..items) } else { list(..items) }
  } else if b.type == "table" {
    let cells = ()
    for row in b.rows {
      for cell in row { cells.push(runs(cell)) }
    }
    table(
      columns: b.header.len(),
      stroke: 0.5pt + luma(170),
      inset: 6pt,
      table.header(..b.header.map(cell => strong(runs(cell)))),
      ..cells,
    )
  } else if b.type == "code" {
    raw(b.text, block: true)
  } else if b.type == "quote" {
    quote(block: true, runs(b.runs))
  } else if b.type == "pagebreak" {
    pagebreak(weak: true)
  } else if b.type == "rule" {
    line(length: 100%, stroke: 0.5pt + luma(170))
  }
}

#for b in data.blocks { render(b) }
