/// 路由包装（窄屏独立页面）。
library;

import 'package:flutter/material.dart';

import 'article_detail_view.dart';

class ArticleDetailPage extends StatelessWidget {
  const ArticleDetailPage({super.key, required this.articleId});

  final int articleId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(),
      body: ArticleDetailView(articleId: articleId),
    );
  }
}
