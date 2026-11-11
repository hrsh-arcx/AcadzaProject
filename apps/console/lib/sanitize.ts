import sanitize from "sanitize-html";

const mathTags =
  "math mrow mi mn mo mtext mspace ms msup msub msubsup mfrac msqrt mroot mstyle mtable mtr mtd mover munder munderover mpadded mphantom menclose mfenced semantics annotation".split(
    " ",
  );
export function safeHtml(value: string): string {
  return sanitize(value, {
    allowedTags: [
      "p",
      "br",
      "span",
      "div",
      "h3",
      "h4",
      "strong",
      "em",
      "b",
      "i",
      "sup",
      "sub",
      "ol",
      "ul",
      "li",
      "table",
      "tr",
      "td",
      ...mathTags,
    ],
    allowedAttributes: {
      math: ["xmlns", "display"],
      "*": [
        "mathvariant",
        "displaystyle",
        "stretchy",
        "fence",
        "form",
        "columnalign",
        "rowalign",
        "width",
        "height",
        "depth",
        "linebreak",
        "encoding",
        "linethickness",
      ],
    },
    disallowedTagsMode: "discard",
  });
}
