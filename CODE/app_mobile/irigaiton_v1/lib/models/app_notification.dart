import 'package:flutter/material.dart';

class AppNotification {
  final String title;
  final String message;
  final DateTime time;
  final String type;

  AppNotification({
    required this.title,
    required this.message,
    required this.time,
    required this.type,
  });
}

// Thay đổi dòng này: Dùng ValueNotifier để phát tín hiệu thay đổi
ValueNotifier<List<AppNotification>> globalNotifications = ValueNotifier([]);