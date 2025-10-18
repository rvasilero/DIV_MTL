
from __future__ import annotations
from typing import List, Optional, Dict, Any
import os

Table = List[List[int]]
Clos  = List[List[bool]]

def _escape_tex(s: str) -> str:
    repl = {
        '\\': r'\textbackslash ',
        '_': r'\_',
        '%': r'\%',
        '&': r'\&',
        '#': r'\#',
        '$': r'\$',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde ',
        '^': r'\textasciicircum ',
    }
    out = []
    for ch in s:
        out.append(repl.get(ch, ch))
    return ''.join(out)

def _latex_matrix(name: str, mat: List[List[int]]) -> str:
    n = len(mat)
    cols = 'r ' + ' '.join(['|'] + ['r'] * n)
    lines = []
    lines.append('\\[\\text{' + _escape_tex(name) + '} = ')
    lines.append('\\begin{array}{' + cols + '}')
    header = ' & ' + ' & '.join(str(j) for j in range(n)) + r' \\ \hline'
    lines.append(header)
    for i, row in enumerate(mat):
        lines.append(str(i) + ' & ' + ' & '.join(str(x) for x in row) + r' \\')
    lines.append(r'\end{array}')
    lines.append(r'\]')
    return '\n'.join(lines)

def _bool_to_int_matrix(tc: Clos) -> List[List[int]]:
    return [[1 if tc[i][j] else 0 for j in range(len(tc))] for i in range(len(tc))]

class LatexAlgebraWriter:
    def __init__(
        self,
        path: str,
        *,
        title: str = 'Algebra Examples',
        author: Optional[str] = None,
        docclass: str = 'article',
        geometry: str = 'margin=1in',
        include_tc: bool = True,
        include_mul: bool = True,
        include_arr: bool = True,
        make_toc: bool = True,
    ) -> None:
        self.path = path
        self.title = title
        self.author = author
        self.docclass = docclass
        self.geometry = geometry
        self.default_include_tc = include_tc
        self.default_include_mul = include_mul
        self.default_include_arr = include_arr
        self.make_toc = make_toc
        self._open = False
        self._ensure_doc_ready()

    def add_summary(self, counts_by_kind: Dict[str, int], section_title: str = 'Summary') -> None:
        self._ensure_open()
        lines = [f"\\section*{{{_escape_tex(section_title)}}}",
                 r"\begin{tabular}{lr}",
                 r"\toprule",
                 "Kind & Iso-classes\\\\\\midrule"]
        for k, v in sorted(counts_by_kind.items()):
            lines.append(f"{_escape_tex(k)} & {v}\\\\")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        self._append("\n".join(lines) + "\n\n")

    def add_example(
        self,
        *,
        kind: str,
        n: int,
        mul: Optional[Table] = None,
        arr: Optional[Table] = None,
        tc: Optional[Clos] = None,
        title: Optional[str] = None,
        label: Optional[str] = None,
        include_tc: Optional[bool] = None,
        include_mul: Optional[bool] = None,
        include_arr: Optional[bool] = None,
        section_level: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._ensure_open()
        inc_tc  = self.default_include_tc if include_tc  is None else include_tc
        inc_mul = self.default_include_mul if include_mul is None else include_mul
        inc_arr = self.default_include_arr if include_arr is None else include_arr

        sec_cmd = {1: "\\section", 2: "\\subsection", 3: "\\subsubsection"}.get(section_level, "\\section")
        hdr = title or f"Class ({_escape_tex(kind)}), n={n}"
        lines = [f"{sec_cmd}{{{_escape_tex(hdr)}}}"]
        if label:
            lines.append(f"\\label{{{_escape_tex(label)}}}")

        if metadata:
            lines.append(r"\begin{description}")
            for k, v in metadata.items():
                lines.append(f"  \item[{_escape_tex(str(k))}] {_escape_tex(str(v))}")
            lines.append(r"\end{description}")

        if inc_mul and mul is not None:
            lines.append(_latex_matrix("*", mul))
        if inc_arr and arr is not None:
            lines.append(_latex_matrix(r"\rightarrow", arr))
        if inc_tc and tc is not None:
            lines.append(_latex_matrix(r"\le", _bool_to_int_matrix(tc)))

        self._append("\n".join(lines) + "\n\n")

    def close(self) -> None:
        if not self._open:
            return
        self._ensure_end_document()
        self._open = False

    def __enter__(self) -> 'LatexAlgebraWriter':
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_doc_ready(self) -> None:
        p = self.path
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            self._write(self._preamble())
        else:
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            stripped = content.rstrip()
            if stripped.endswith(r"\end{document}"):
                stripped = stripped[: -len(r"\end{document}")].rstrip()
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(stripped + '\n')
        self._open = True

    def _ensure_open(self) -> None:
        if not self._open:
            self._ensure_doc_ready()

    def _ensure_end_document(self) -> None:
        with open(self.path, 'r', encoding='utf-8') as f:
            content = f.read().rstrip()
        if not content.endswith(r"\end{document}"):
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write("\\end{document}\n")

    def _append(self, s: str) -> None:
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(s)

    def _write(self, s: str) -> None:
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(s)

    def _preamble(self) -> str:
        title = _escape_tex(self.title)
        author_line = ("\\author{" + _escape_tex(self.author) + "}\n") if self.author else ""
        toc = "\\tableofcontents\n" if self.make_toc else ""
        return ("\\documentclass[11pt]{" + _escape_tex(self.docclass) + "}\n"
                + "\\usepackage[" + _escape_tex(self.geometry) + "]{geometry}\n"
                + "\\usepackage{amsmath,amssymb}\n"
                + "\\usepackage{booktabs}\n"
                + "\\title{" + title + "}\n"
                + author_line
                + "\\date{}\n"
                + "\\begin{document}\\maketitle\n"
                + toc)
