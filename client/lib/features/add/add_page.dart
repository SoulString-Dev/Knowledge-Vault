/// 添加页（FR1.1 / 6.4）：URL 与粘贴文本两个入口；
/// 桌面端打开时自动检测剪贴板中的合法 URL 并预填（不做失焦/后台全局快捷键）。
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/session.dart';
import '../../l10n/generated/app_localizations.dart';

final _urlRe = RegExp(r'^https?://\S+$', caseSensitive: false);

class AddPage extends ConsumerStatefulWidget {
  const AddPage({super.key});

  @override
  ConsumerState<AddPage> createState() => _AddPageState();
}

class _AddPageState extends ConsumerState<AddPage> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);
  final _urlCtrl = TextEditingController();
  final _pasteTitleCtrl = TextEditingController();
  final _pasteCtrl = TextEditingController();
  bool _submitting = false;
  String? _error;
  String? _clipboardNote;

  @override
  void initState() {
    super.initState();
    _detectClipboard();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _urlCtrl.dispose();
    _pasteTitleCtrl.dispose();
    _pasteCtrl.dispose();
    super.dispose();
  }

  /// 桌面与移动端在打开添加页时读取剪贴板；合法 URL 才预填（FR1.1 的实现口径）。
  Future<void> _detectClipboard() async {
    try {
      final data = await Clipboard.getData(Clipboard.kTextPlain);
      final text = data?.text?.trim() ?? '';
      if (text.isNotEmpty && _urlRe.hasMatch(text) && mounted) {
        setState(() {
          _urlCtrl.text = text;
          _clipboardNote = AppLocalizations.of(context).addClipboardFound;
        });
      }
    } on PlatformException {
      // 剪贴板不可用（如桌面无显示环境）时静默跳过
    }
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    final isUrl = _tabs.index == 0;
    if (isUrl && !_urlRe.hasMatch(_urlCtrl.text.trim())) {
      setState(() => _error = l10n.invalidUrl);
      return;
    }
    if (!isUrl && _pasteCtrl.text.trim().isEmpty) {
      setState(() => _error = l10n.requiredField);
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final api = ref.read(vaultApiProvider);
      if (isUrl) {
        await api.createArticle(_urlCtrl.text.trim());
      } else {
        await api.pasteArticle(title: _pasteTitleCtrl.text.trim(), text: _pasteCtrl.text);
      }
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(l10n.addSubmitted)));
        context.pop();
      }
    } on ApiError catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n.addTitle)),
      body: Column(
        children: [
          TabBar(
            controller: _tabs,
            tabs: [
              Tab(text: l10n.addUrlTab),
              Tab(text: l10n.addPasteTab),
            ],
            onTap: (_) => setState(() {}),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_clipboardNote != null) ...[
                  Text(_clipboardNote!, style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 8),
                ],
                if (_tabs.index == 0)
                  TextFormField(
                    controller: _urlCtrl,
                    decoration: InputDecoration(
                      labelText: l10n.addUrlLabel,
                      hintText: l10n.addUrlHint,
                    ),
                    keyboardType: TextInputType.url,
                    autofocus: true,
                  )
                else ...[
                  TextFormField(
                    controller: _pasteTitleCtrl,
                    decoration: InputDecoration(labelText: l10n.addPasteTitleLabel),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _pasteCtrl,
                    decoration: InputDecoration(labelText: l10n.addPasteTextLabel),
                    maxLines: 12,
                    autofocus: true,
                  ),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () async {
                        final data = await Clipboard.getData(Clipboard.kTextPlain);
                        if (data?.text != null && mounted) {
                          setState(() => _pasteCtrl.text = data!.text!);
                        }
                      },
                      child: Text(l10n.addPasteFromClipboard),
                    ),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: _submitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(l10n.addSubmit),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
