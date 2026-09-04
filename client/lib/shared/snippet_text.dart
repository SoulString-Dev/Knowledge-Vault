/// 服务端返回的命中片段：`<em>…</em>` 高亮渲染为强调样式。
library;

import 'package:flutter/material.dart';

class SnippetText extends StatelessWidget {
  const SnippetText({super.key, this.snippet, this.maxLines = 3});

  final String? snippet;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    final text = snippet ?? '';
    if (text.isEmpty) {
      return const SizedBox.shrink();
    }
    final spans = _buildSpans(context, text);
    return RichText(
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
      text: TextSpan(
        style: Theme.of(
          context,
        ).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
        children: spans,
      ),
    );
  }

  List<InlineSpan> _buildSpans(BuildContext context, String text) {
    final highlight = Theme.of(context).colorScheme.primary;
    final spans = <InlineSpan>[];
    final pattern = RegExp(r'<em>(.*?)</em>', dotAll: true);
    int cursor = 0;
    for (final match in pattern.allMatches(text)) {
      if (match.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, match.start)));
      }
      spans.add(
        TextSpan(
          text: match.group(1),
          style: TextStyle(color: highlight, fontWeight: FontWeight.bold),
        ),
      );
      cursor = match.end;
    }
    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor)));
    }
    return spans;
  }
}
