import 'package:flutter/material.dart';
import '../models/app_notification.dart';
import 'package:intl/intl.dart';

class NotificationView extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Thông báo hệ thống")),
      // Widget này là "chìa khóa" để cập nhật ngay lập tức
      body: ValueListenableBuilder<List<AppNotification>>(
        valueListenable: globalNotifications,
        builder: (context, notifications, child) {
          if (notifications.isEmpty) {
            return Center(child: Text("Chưa có thông báo nào"));
          }
          return ListView.builder(
            itemCount: notifications.length,
            itemBuilder: (context, index) {
              final item = notifications[index];
              return Card(
                margin: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                child: ListTile(
                  leading: Icon(item.type == 'pump' ? Icons.settings_input_component : Icons.settings),
                  title: Text(item.title),
                  subtitle: Text(DateFormat('HH:mm:ss').format(item.time)),
                ),
              );
            },
          );
        },
      ),
    );
  }
}