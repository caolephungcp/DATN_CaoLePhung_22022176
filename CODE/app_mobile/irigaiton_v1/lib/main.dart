import 'package:flutter/material.dart';
import 'package:irigaiton_v1/views/home_view.dart';
import 'views/login_view.dart';
import 'views/dashboard_view.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Irrigation App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.green,
      ),
      home: LoginView(), // Chạy màn hình đăng nhập đầu tiên
    );
  }
}

// caolephungcp@gmail.com
// Songngu2702.
