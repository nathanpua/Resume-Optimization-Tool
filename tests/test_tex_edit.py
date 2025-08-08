from resume_ai.tex_edit import extract_itemize_blocks, replace_itemize_block, set_header_availability


def test_itemize_roundtrip():
    src = r"""Before
\begin{itemize}
\item A
\item B
\end{itemize}
After"""
    blocks = extract_itemize_blocks(src)
    assert len(blocks) == 1
    block, items = blocks[0]
    assert items == ["A", "B"]
    out = replace_itemize_block(src, block, ["X", "Y", "Z"])
    assert "\\item X" in out and "\\item Z" in out


def test_header_availability():
    src = "\\resumeheader{Name}{Loc}{Avail}{email@x.com}{https://x.com}"
    # None -> unchanged
    out = set_header_availability(src, None)
    assert out == src
    # Empty string -> clears availability field
    out2 = set_header_availability(src, "")
    assert "}{email@x.com}" in out2 and "Avail" not in out2
