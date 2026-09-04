/// 命中片段 <em> 高亮渲染测试。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:knowledge_vault/shared/snippet_text.dart';

void main() {
  testWidgets('SnippetText 将 <em> 拆分为三段并加粗高亮', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: SnippetText(snippet: '…可重入锁的<em>坑</em>主要有三点…')),
      ),
    );
    final rich = tester.widget<RichText>(find.byType(RichText));
    final spans = (rich.text as TextSpan).children!;
    expect(spans.length, 3);
    expect((spans[0] as TextSpan).text, '…可重入锁的');
    expect((spans[1] as TextSpan).text, '坑');
    expect((spans[1] as TextSpan).style?.fontWeight, FontWeight.bold);
    expect((spans[2] as TextSpan).text, '主要有三点…');
  });

  testWidgets('无 <em> 时为单段文本；空串不渲染 RichText', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: SnippetText(snippet: '普通片段'))),
    );
    final rich = tester.widget<RichText>(find.byType(RichText));
    expect((rich.text as TextSpan).children!.length, 1);

    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: SnippetText(snippet: ''))),
    );
    expect(find.byType(RichText), findsNothing);
  });
}
