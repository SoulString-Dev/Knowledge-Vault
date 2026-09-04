/// 检索页（FR3.1–3.3）：混合 / 关键词 / 语义模式切换、标签与状态过滤、命中片段高亮。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/session.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../shared/snippet_text.dart';
import '../../shared/status_chip.dart';

class SearchPage extends ConsumerStatefulWidget {
  const SearchPage({super.key});

  @override
  ConsumerState<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends ConsumerState<SearchPage> {
  final _query = TextEditingController();
  String _mode = 'hybrid';
  int? _tagFilter;
  String? _statusFilter;
  List<Tag> _tags = [];
  SearchResponse? _result;
  bool _searching = false;
  String? _error;
  bool _searched = false;

  @override
  void initState() {
    super.initState();
    _loadTags();
  }

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _loadTags() async {
    try {
      final tags = await ref.read(vaultApiProvider).tags();
      if (mounted) setState(() => _tags = tags);
    } on ApiError {
      // 标签加载失败不阻塞搜索
    }
  }

  Future<void> _run() async {
    if (_query.text.trim().isEmpty) return;
    setState(() {
      _searching = true;
      _error = null;
      _searched = true;
    });
    try {
      final result = await ref
          .read(vaultApiProvider)
          .search(query: _query.text.trim(), mode: _mode, tagId: _tagFilter, status: _statusFilter);
      if (mounted) setState(() => _result = result);
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.searchTitle)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _query,
              decoration: InputDecoration(
                hintText: l10n.searchHint,
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: _searching ? null : _run,
                ),
              ),
              onSubmitted: (_) => _run(),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                SegmentedButton<String>(
                  segments: [
                    ButtonSegment(value: 'hybrid', label: Text(l10n.modeHybrid)),
                    ButtonSegment(value: 'keyword', label: Text(l10n.modeKeyword)),
                    ButtonSegment(value: 'semantic', label: Text(l10n.modeSemantic)),
                  ],
                  selected: {_mode},
                  onSelectionChanged: (s) {
                    setState(() => _mode = s.first);
                    _run();
                  },
                ),
                const SizedBox(width: 8),
                DropdownButton<int?>(
                  value: _tagFilter,
                  hint: Text(l10n.filterTag),
                  underline: const SizedBox.shrink(),
                  items: [
                    DropdownMenuItem<int?>(child: Text(l10n.statusAll)),
                    for (final t in _tags) DropdownMenuItem<int?>(value: t.id, child: Text(t.name)),
                  ],
                  onChanged: (v) {
                    setState(() => _tagFilter = v);
                    _run();
                  },
                ),
              ],
            ),
          ),
          Expanded(child: _buildResults(l10n)),
        ],
      ),
    );
  }

  Widget _buildResults(AppLocalizations l10n) {
    if (_searching) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text(_error!));
    if (!_searched) return Center(child: Text(l10n.searchFirst));
    final result = _result;
    if (result == null || result.results.isEmpty) {
      return Center(child: Text(l10n.noResults));
    }
    return ListView.builder(
      itemCount: result.results.length,
      itemBuilder: (context, index) {
        final hit = result.results[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        hit.title ?? hit.url,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    StatusChip(status: hit.status),
                  ],
                ),
                const SizedBox(height: 6),
                SnippetText(snippet: hit.snippet),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  children: [
                    for (final m in hit.matchedBy)
                      Text(
                        m == 'keyword' ? l10n.matchedKeyword : l10n.matchedSemantic,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    for (final t in hit.tags)
                      Text(t, style: Theme.of(context).textTheme.labelSmall),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
