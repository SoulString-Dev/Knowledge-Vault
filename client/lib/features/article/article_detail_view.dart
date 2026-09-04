/// 阅读视图（FR4.2 / 6.3，M2 为只读渲染 + 人工修正入口）：
/// 摘要卡、标签行、Markdown 正文；处理中自动轮询（3s→5s→10s）；
/// 菜单：编辑标题 / 摘要（PATCH 触发服务端重算索引与向量）、重新分析、删除。
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:markdown_widget/markdown_widget.dart';

import '../../core/session.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../shared/status_chip.dart';

const _pollIntervals = [Duration(seconds: 3), Duration(seconds: 5), Duration(seconds: 10)];

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

class ArticleDetailView extends ConsumerStatefulWidget {
  const ArticleDetailView({super.key, required this.articleId, this.embedded = false});

  final int articleId;
  final bool embedded; // 宽屏双栏嵌入时不自带 Scaffold

  @override
  ConsumerState<ArticleDetailView> createState() => _ArticleDetailViewState();
}

class _ArticleDetailViewState extends ConsumerState<ArticleDetailView> {
  ArticleDetail? _detail;
  bool _loading = true;
  String? _error;
  Timer? _pollTimer;
  int _pollIndex = 0;

  VaultApi get _api => ref.read(vaultApiProvider);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ArticleDetailView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.articleId != widget.articleId) {
      _pollTimer?.cancel();
      _pollIndex = 0;
      _detail = null;
      _load();
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final detail = await _api.article(widget.articleId);
      if (!mounted) return;
      setState(() => _detail = detail);
      _schedulePoll();
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _schedulePoll() {
    _pollTimer?.cancel();
    if (_detail == null || !_detail!.article.isProcessing) return;
    _pollTimer = Timer(_pollIntervals[_pollIndex.clamp(0, _pollIntervals.length - 1)], () {
      _pollIndex = (_pollIndex + 1).clamp(0, _pollIntervals.length - 1);
      _load(silent: true);
    });
  }

  Future<void> _editField({required bool editTitle}) async {
    final l10n = AppLocalizations.of(context);
    final article = _detail!.article;
    final ctrl = TextEditingController(text: editTitle ? (article.title ?? '') : (article.summary ?? ''));
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(editTitle ? l10n.editTitle : l10n.editSummary),
        content: TextField(controller: ctrl, maxLines: editTitle ? 1 : 4, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text), child: Text(l10n.save)),
        ],
      ),
    );
    if (value == null) return;
    await _api.patchArticle(article.id, title: editTitle ? value : null, summary: editTitle ? null : value);
    await _load(silent: true);
  }

  Future<void> _reanalyze() async {
    await _api.reanalyze(_detail!.article.id);
    _pollIndex = 0;
    await _load(silent: true);
  }

  Future<void> _delete() async {
    final l10n = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(l10n.deleteConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.delete)),
        ],
      ),
    );
    if (confirmed != true) return;
    await _api.deleteArticle(_detail!.article.id);
    if (mounted && !widget.embedded) {
      context.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (_loading && _detail == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(child: Text(_error!));
    }
    final detail = _detail!;
    final article = detail.article;

    final menu = PopupMenuButton<String>(
      onSelected: (action) async {
        switch (action) {
          case 'edit_title':
            await _editField(editTitle: true);
          case 'edit_summary':
            await _editField(editTitle: false);
          case 'reanalyze':
            await _reanalyze();
          case 'delete':
            await _delete();
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem(value: 'edit_title', child: Text(l10n.editTitle)),
        PopupMenuItem(value: 'edit_summary', child: Text(l10n.editSummary)),
        if (article.status == 'failed' || article.status == 'ready')
          PopupMenuItem(value: 'reanalyze', child: Text(l10n.reanalyze)),
        PopupMenuItem(value: 'delete', child: Text(l10n.delete)),
      ],
    );

    final body = SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  article.title ?? article.url,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              const SizedBox(width: 8),
              menu,
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              StatusChip(status: article.status),
              const SizedBox(width: 8),
              if (article.wordCount != null)
                Text(
                  l10n.wordCount(article.wordCount!),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          ),
          if (article.isProcessing) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                const SizedBox(width: 8),
                Text(l10n.processingHint, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ],
          if (article.status == 'failed' && article.error != null) ...[
            const SizedBox(height: 12),
            Text(
              '${l10n.failedHint}：${article.error}',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (article.summary != null && article.summary!.isNotEmpty) ...[
            const SizedBox(height: 16),
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l10n.summary, style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 6),
                    Text(article.summary!),
                  ],
                ),
              ),
            ),
          ],
          if (detail.tags.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [for (final t in detail.tags) Chip(label: Text(t.name))],
            ),
          ],
          const SizedBox(height: 16),
          if (detail.contentMd != null && detail.contentMd!.isNotEmpty)
            MarkdownWidget(data: detail.contentMd!)
          else if (!article.isProcessing)
            Text(l10n.noSummary, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );

    if (widget.embedded) {
      return body;
    }
    return Scaffold(appBar: AppBar(), body: body);
  }
}
