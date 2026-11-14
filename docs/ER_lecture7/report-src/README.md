# LaTeX 报告源文件

主文件为 [CS307_Project1_Report.tex](CS307_Project1_Report.tex)。修改正文、表格或命令时直接编辑该文件。插图在 `figures/`，编译时需与主文件一起保留。

使用包含 CTeX、LuaTeX-ja 和 Fandol 字体的 TeX Live，在本目录执行两次 LuaLaTeX。PDF 会嵌入中文字体及字符映射。

```powershell
lualatex -interaction=nonstopmode -halt-on-error CS307_Project1_Report.tex
lualatex -interaction=nonstopmode -halt-on-error CS307_Project1_Report.tex
```

若使用 Overleaf，上传 TeX 主文件和 `figures/`，将编译器设为 LuaLaTeX。编译生成的 PDF 可以复制到上一级目录，作为 `CS307_Project1_Report.pdf`。

概念 E-R 图的可编辑源文件在上一级目录。用 draw.io 更新后，导出 PNG 覆盖 `figures/concept-er.png`，再重新编译报告。
