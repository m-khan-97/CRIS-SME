# Architecture Diagram Sources

GitHub pages embed the checked-in SVG files so diagrams render without relying
on GitHub's Mermaid rich-display service.

The principal architecture diagrams use Graphviz DOT:

```bash
dot -Tsvg docs/diagrams/readme-overview.dot \
  -o docs/diagrams/readme-overview.svg
dot -Tsvg docs/diagrams/component-architecture.dot \
  -o docs/diagrams/component-architecture.svg
```

The remaining `.mmd` files are editable Mermaid sources for sequence and compact
supporting views. Their generated SVGs are also committed for reliable browser
display.

When changing a diagram, update its source and regenerated SVG in the same
commit. Use a white graph background so labels remain readable in both GitHub
light and dark themes.
