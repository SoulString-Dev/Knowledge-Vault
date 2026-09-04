/// 卡片状态徽标（pending / processing / ready / failed）。
library;

import 'package:flutter/material.dart';

import '../../l10n/generated/app_localizations.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final (label, color) = switch (status) {
      'pending' => (l10n.statusPending, Colors.orange),
      'processing' => (l10n.statusProcessing, Colors.blue),
      'ready' => (l10n.statusReady, Colors.green),
      'failed' => (l10n.statusFailed, Colors.red),
      _ => (status, Colors.grey),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label, style: TextStyle(fontSize: 12, color: color)),
    );
  }
}
