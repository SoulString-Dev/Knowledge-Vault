/// 知识流列表卡片。
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart' as intl;

import '../core/models.dart';
import 'status_chip.dart';

class ArticleCard extends StatelessWidget {
  const ArticleCard({super.key, required this.article, required this.onTap, this.selected = false});

  final Article article;
  final VoidCallback onTap;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final created = article.createdAt == null
        ? ''
        : ' · ${intl.DateFormat.yMd().add_Hm().format(article.createdAt!.toLocal())}';
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      child: ListTile(
        selected: selected,
        onTap: onTap,
        title: Text(
          article.title ?? article.url,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.titleMedium,
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Row(
              children: [
                StatusChip(status: article.status),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${article.domain ?? ''}$created',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall,
                  ),
                ),
              ],
            ),
            if (article.summary != null && article.summary!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                article.summary!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
