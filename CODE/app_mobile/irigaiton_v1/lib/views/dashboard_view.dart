import 'package:flutter/material.dart';
import 'home_view.dart';
import 'history_view.dart';
import 'notification_view.dart';
import '../services/auth_service.dart';
import 'login_view.dart';

class DashboardView extends StatefulWidget {
  @override
  _DashboardViewState createState() => _DashboardViewState();
}

class _DashboardViewState extends State<DashboardView> {
  int _selectedIndex = 0;
  final AuthService _authService = AuthService();

  // Danh sách các trang con
  final List<Widget> _views = [
    HomeView(),
    HistoryView(),
    NotificationView(),
  ];

  // Hàm xử lý đăng xuất chuyên nghiệp
  void _handleLogout() async {
    // Hiển thị hộp thoại xác nhận trước khi thoát
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text("Đăng xuất"),
        content: Text("Bạn có chắc chắn muốn thoát hệ thống không?"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text("HỦY", style: TextStyle(color: Colors.grey)),
          ),
          TextButton(
            onPressed: () async {
              await _authService.logout();
              if (!mounted) return;
              // Xóa toàn bộ stack và quay về màn hình Login
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (context) => LoginView()),
                (route) => false,
              );
            },
            child: Text("ĐĂNG XUẤT", style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // --- HEADER (APPBAR) CHUNG CHO TOÀN BỘ APP ---
      appBar: AppBar(
        elevation: 2,
        backgroundColor: Colors.green,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Irrigation System",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            Text(
              "caolephungcp@gmail.com", // Sau này có thể thay bằng biến động
              style: TextStyle(fontSize: 12, color: Colors.white70),
            ),
          ],
        ),
        actions: [
          // Menu xổ xuống ở góc phải
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'logout') {
                _handleLogout();
              }
            },
            icon: CircleAvatar(
              backgroundColor: Colors.white24,
              child: Icon(Icons.person, color: Colors.white, size: 20),
            ),
            itemBuilder: (BuildContext context) => [
              PopupMenuItem(
                value: 'profile',
                child: Row(
                  children: [
                    Icon(Icons.account_circle_outlined, color: Colors.black54),
                    SizedBox(width: 10),
                    Text("Tài khoản"),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout, color: Colors.red),
                    SizedBox(width: 10),
                    Text("Đăng xuất", style: TextStyle(color: Colors.red)),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(width: 8),
        ],
      ),

      // --- NỘI DUNG THAY ĐỔI THEO TAB ---
      body: IndexedStack(
        index: _selectedIndex,
        children: _views,
      ),

      // --- THANH ĐIỀU HƯỚNG DƯỚI CÙNG ---
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        selectedItemColor: Colors.green,
        unselectedItemColor: Colors.grey,
        showUnselectedLabels: true,
        type: BottomNavigationBarType.fixed,
        items: [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            activeIcon: Icon(Icons.home),
            label: "Trang chủ",
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.analytics_outlined),
            activeIcon: Icon(Icons.analytics),
            label: "Đồ thị",
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.notifications_none),
            activeIcon: Icon(Icons.notifications),
            label: "Thông báo",
          ),
        ],
      ),
    );
  }
}