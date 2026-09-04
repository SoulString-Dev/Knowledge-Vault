/// 知识流（FR4.2 / FR4.5）：状态筛选、下拉刷新、分页、处理中卡片轮询（3s→5s→10s 退避，
/// 应用退后台暂停，6.5）；宽屏（≥1000dp）列表 + 详情双栏（FR4.6）。
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/session.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../shared/article_card.dart';
import '../article/article_detail_view.dart';

const _pollIntervals = [Duration(seconds: 3), Duration(seconds: 5), Duration(seconds: 10)];

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage>
    with WidgetsBindingObserver {
  final _scroll = ScrollController();
  final _searchCtrl = TextEditingController();
  List<Article> _items = [];
  int _total = 0;
  int _page = 1;
  String? _statusFilter;
  bool _loading = false;
  bool _loadingMore = false;
  String? _error;
  int _selectedId = -1;

  // 轮询
  Timer? _pollTimer;
  int _pollIndex = 0;
  bool _resumed = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _scroll.addListener(_onScroll);
    _refresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pollTimer?.cancel();
    _scroll.removeListener(_onScroll);
    _scroll.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 6.5：退后台暂停轮询，回前台恢复
    _resumed = state == AppLifecycleState.resumed;
    if (_resumed) _scheduleNextPoll();
  }

  void _onScroll() {
    if (_scroll.position.extentAfter < 400 &&
        !_loading &&
        !_loadingMore &&
        _items.length < _total) {
      _loadMore();
    }
  }

  VaultApi get _api => ref.read(vaultApiProvider);

  Future<void> _refresh() async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await _api.articles(
        page: 1,
        status: _statusFilter,
        q: _searchCtrl.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _items = page.items;
        _total = page.total;
        _page = 1;
      });
      _scheduleNextPoll();
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore) return;
    setState(() => _loadingMore = true);
    try {
      final next = await _api.articles(
        page: _page + 1,
        status: _statusFilter,
        q: _searchCtrl.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _page += 1;
        _total = next.total;
        final known = _items.map((a) => a.id).toSet();
        _items.addAll(next.items.where((a) => !known.contains(a.id)));
      });
    } on ApiError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  /// 有 pending/processing 卡片时静默刷新第一页；连续成功则退避 3s→5s→10s。
  void _scheduleNextPoll() {
    _pollTimer?.cancel();
    final hasProcessing = _items.any((a) => a.isProcessing);
    if (!hasProcessing || !_resumed) return;
    _pollTimer = Timer(_pollIntervals[_pollIndex.clamp(0, _pollIntervals.length - 1)], () async {
      if (!_resumed || !mounted) return;
      try {
        final page = await _api.articles(
          page: 1,
          status: _statusFilter,
          q: _searchCtrl.text.trim(),
        );
        if (!mounted) return;
        setState(() => _items = page.items);
        _pollIndex = (page.items.any((a) => a.isProcessing))
            ? (_pollIndex + 1).clamp(0, _pollIntervals.length - 1)
            : 0;
        if (page.items.any((a) => a.isProcessing)) _scheduleNextPoll();
      } on ApiError {
        _scheduleNextPoll();
      }
    });
  }

  void _openArticle(Article article) {
    final wide = MediaQuery.of(context).size.width >= 1000;
    if (wide) {
      setState(() => _selectedId = article.id);
    } else {
      context.push('/article/${article.id}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final wide = MediaQuery.of(context).size.width >= 1000;
    final statuses = <String?>[null, 'pending', 'processing', 'ready', 'failed'];

    final list = Scaffold(
      appBar: AppBar(
        title: Text(l10n.homeTitle),
        actions: [
          IconButton(
            tooltip: l10n.tagsTitle,
            icon: const Icon(Icons.label_outline),
            onPressed: () => context.push('/tags'),
          ),
          IconButton(
            tooltip: l10n.settingsTitle,
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await context.push('/add');
          _refresh();
        },
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: TextField(
              controller: _searchCtrl,
              readOnly: true,
              decoration: InputDecoration(
                hintText: l10n.searchHint,
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _searchCtrl.clear();
                    _refresh();
                  },
                ),
              ),
              onTap: () => context.push('/search'),
            ),
          ),
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                for (final s in statuses)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(
                        s == null
                            ? l10n.statusAll
                            : switch (s) {
                                'pending' => l10n.statusPending,
                                'processing' => l10n.statusProcessing,
                                'ready' => l10n.statusReady,
                                _ => l10n.statusFailed,
                              },
                      ),
                      selected: _statusFilter == s,
                      onSelected: (_) {
                        setState(() => _statusFilter = s);
                        _refresh();
                      },
                    ),
                  ),
              ],
            ),
          ),
          Expanded(child: _buildList(l10n)),
        ],
      ),
    );

    if (!wide) return list;
    // 宽屏双栏：列表 + 阅读视图（FR4.6）
    return Scaffold(
      appBar: AppBar(title: Text(l10n.homeTitle)),
      body: Row(
        children: [
          SizedBox(width: 420, child: list),
          const VerticalDivider(width: 1),
          Expanded(
            child: _selectedId < 0
                ? Center(child: Text(l10n.detailPlaceholder))
                : ArticleDetailView(articleId: _selectedId, embedded: true),
          ),
        ],
      ),
    );
  }

  Widget _buildList(AppLocalizations l10n) {
    if (_loading && _items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            TextButton(onPressed: _refresh, child: Text(l10n.done)),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return Center(
        child: Text(
          (_statusFilter == null && _searchCtrl.text.isEmpty)
              ? l10n.emptyList
              : l10n.emptyListFiltered,
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.builder(
        controller: _scroll,
        itemCount: _items.length + (_loadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= _items.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            );
          }
          final article = _items[index];
          return ArticleCard(
            article: article,
            selected: article.id == _selectedId,
            onTap: () => _openArticle(article),
          );
        },
      ),
    );
  }
}
