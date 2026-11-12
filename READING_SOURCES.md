# 内置阅读文本来源

本应用仅打包下列古典原文数据，不提供现代出版社注释、译文、赏析或受保护的书籍全文。

来源项目：chinese-poetry/chinese-poetry；获取日期：2026-11-12；许可：MIT，完整许可保留于 THIRD_PARTY_LICENSES.txt。

- 唐诗原文库：[来源文件](https://github.com/chinese-poetry/chinese-poetry/blob/master/全唐诗/唐诗三百首.json)，Git blob SHA：c9522d59b11bf3cd600fffba694fd3d3b4714982，原始数据 366 条。
- 宋词原文库：[来源文件](https://github.com/chinese-poetry/chinese-poetry/blob/master/宋词/宋词三百首.json)，Git blob SHA：7f5bfd0efbb601655b3475468c01ebe91d45c344，原始数据 280 条。

仅提取 title/rhythmic、author、paragraphs 字段生成 reading.js，未复制其他解说字段。文本保留来源的文字与排列方式，未逐篇校勘，可能存在重复、异文与缺漏；不将其宣传为指定出版版本的完整电子书。

《唐诗三百首（金性尧注本）》书卡打开的是古诗原文库，不含金性尧注释。《宋词三百首》书卡打开的是第三方古词原文库，目录与出版版本可能不同。

其他书籍仅提供微信读书的书名搜索入口。不保证每部作品在平台上架、免费或具有指定译本；登录、阅读权限和站外进度由平台处理。站外页面不嵌入本应用，应用无法自动读取站外的阅读位置。

## 简体转换与学习辅助（2026-11-12）

显示文本使用 OpenCC 的 TSCharacters / TSPhrases 字典进行最长匹配转换，并对转换结果作稳定性检查。OpenCC 数据依据 Apache-2.0 许可保留在 sources/opencc-*，完整许可见 sources/OpenCC-LICENSE.txt。转换前文本保留在 sources/poetry-original.json；篇目 ID 不变。

poetry-guides.js 含 42 篇原创简要释义与赏析，以及 604 篇明确标示为辅助导读的记录。后者由文本词语、常见古今义和主题阅读问题整理，不是逐句白话译文，也不是经校核的典故注本。不得宣传为所有篇目均有完整精注。

## 英文原版

新增 6 本英语原版：The Tale of Peter Rabbit；The Happy Prince and Other Tales；Aesop’s Fables（V. S. Vernon Jones 英译）；Alice’s Adventures in Wonderland；The Wonderful Wizard of Oz；The Secret Garden。

- 四本来自 GitHub 的 standardebooks 公版原版项目，贡献采用 CC0 1.0。下载归档的 SHA-256、具体仓库地址、篇章数量记录于 sources/manifest.json；每本保留 uncopyright 许可页。仅提取正文，没有运行来源仓库中的代码。
- Peter Rabbit 与 Happy Prince 来自 Project Gutenberg，完整来源文本及其许可保留于 sources/en001-source.txt、sources/en002-source.txt，阅读器亦链接原始来源。只使用旧版原文，不复制现代改写或译文。
- 页面上的难度范围、阅读顺序和练习方法是本应用的编辑建议，不是 CEFR 官方分级或效果保证。经典原著存在古旧语言、方言或文字游戏。
- 听读使用浏览器 SpeechSynthesis 合成语音，不是真人录音。不录音、不评分；可用英语音色取决于浏览器和设备。自动化验收仅检查朗读调用与交互，不验证发声质量。

## 可立即阅读的公版原典拓展

新增《诗经》《论语》《大学》《孟子》简体原文，保留原书单。数据来自 chinese-poetry/chinese-poetry（MIT），来源路径及 Git blob SHA 保留在 sources/alternatives-original.json，仅复制古代原文，未附现代译注。生成命令为 `python3 scripts/add_public_alternatives.py`。截至本次更新，主目录共 68 项，已内置 12 项文本；原书单中尚未接入全文的 56 项仍保留，不把新增原典标成这些书的同版全文。
