/// 标签管理（F6）：列表 + 计数、重命名、删除、合并。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/session.dart';
import '../../l10n/generated/app_localizations.dart';

class TagsPage extends ConsumerStatefulWidget {
  const TagsPage({super.key});

  @override
  ConsumerState<TagsPage> createState() => _TagsPageState();
}

class _TagsPageState extends ConsumerState<TagsPage> {
  List<Tag> _tags = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final tags = await ref.read(vaultApiProvider).tags();
      if (mounted) setState(() => _tags = tags);
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _rename(Tag tag) async {
    final l10n = AppLocalizations.of(context);
    final ctrl = TextEditingController(text: tag.name);
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.renameTag),
        content: TextField(controller: ctrl, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text), child: Text(l10n.save)),
        ],
      ),
    );
    if (name == null || name.trim().isEmpty || name.trim() == tag.name) return;
    try {
      await ref.read(vaultApiProvider).renameTag(tag.id, name.trim());
      await _load();
    } on ApiError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _delete(Tag tag) async {
    final l10n = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(l10n.deleteTagConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(l10n.delete)),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(vaultApiProvider).deleteTag(tag.id);
      await _load();
    } on ApiError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _merge(Tag tag) async {
    final l10n = AppLocalizations.of(context);
    final candidates = _tags.where((t) => t.id != tag.id).toList();
    if (candidates.isEmpty) return;
    final target = await showDialog<Tag>(
      context: context,
      builder: (context) => SimpleDialog(
        title: Text(l10n.mergeTagInto(tag.name)),
        children: [
          for (final t in candidates)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(context, t),
              child: Text('${t.name}（${t.articleCount}）'),
            ),
        ],
      ),
    );
    if (target == null) return;
    try {
      await ref.read(vaultApiProvider).mergeTag(tag.id, target.id);
      await _load();
    } on ApiError catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.tagsTitle)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(child: Text(_error!))
          : _tags.isEmpty
          ? Center(child: Text(l10n.noTags))
          : ListView.builder(
              itemCount: _tags.length,
              itemBuilder: (context, index) {
                final tag = _tags[index];
                return ListTile(
                  leading: const Icon(Icons.label_outline),
                  title: Text(tag.name),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(l10n.tagCount(tag.articleCount)),
                      PopupMenuButton<String>(
                        onSelected: (action) async {
                          switch (action) {
                            case 'rename':
                              await _rename(tag);
                            case 'merge':
                              await _merge(tag);
                            case 'delete':
                              await _delete(tag);
                          }
                        },
                        itemBuilder: (context) => [
                          PopupMenuItem(value: 'rename', child: Text(l10n.renameTag)),
                          PopupMenuItem(value: 'merge', child: Text(l10n.mergeTag)),
                          PopupMenuItem(value: 'delete', child: Text(l10n.delete)),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
