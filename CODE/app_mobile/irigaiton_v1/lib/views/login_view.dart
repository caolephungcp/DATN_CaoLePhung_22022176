import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'dashboard_view.dart'; // Màn hình chính bạn sẽ tạo sau

class LoginView extends StatefulWidget {
  @override
  _LoginViewState createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _authService = AuthService();
  bool _isLoading = false;
  bool _isPasswordVisible = false; // Mặc định là ẩn (false)

  void _handleLogin() async {
    setState(() => _isLoading = true);
    
    bool success = await _authService.login(
      _emailController.text.trim(),
      _passwordController.text.trim(),
    );

    setState(() => _isLoading = false);

    if (success) {
      // Đăng nhập thành công, chuyển hướng sang Dashboard
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => DashboardView()),
      );
    } else {
      // Thông báo lỗi
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Đăng nhập thất bại. Vui lòng kiểm tra lại!")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.agriculture, size: 100, color: Colors.green),
            SizedBox(height: 20),
            Text("Hệ thống Tưới Ngô Thông Minh", 
                 style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.green)),
            SizedBox(height: 40),
            TextField(
              controller: _emailController,
              decoration: InputDecoration(labelText: "Email/Username", border: OutlineInputBorder()),
            ),
            SizedBox(height: 20),
            TextField(
              controller: _passwordController,
              obscureText: !_isPasswordVisible, // Đảo ngược giá trị của biến để ẩn/hiện
              decoration: InputDecoration(
                labelText: "Mật khẩu",
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.lock), // Thêm icon khóa phía trước cho đẹp
                suffixIcon: IconButton(
                  icon: Icon(
                    // Thay đổi icon dựa trên trạng thái
                    _isPasswordVisible ? Icons.visibility : Icons.visibility_off,
                    color: Colors.grey,
                  ),
                  onPressed: () {
                    // Khi nhấn vào thì đảo ngược giá trị hiện tại
                    setState(() {
                      _isPasswordVisible = !_isPasswordVisible;
                    });
                  },
                ),
              ),
            ),
            SizedBox(height: 30),
            _isLoading 
              ? CircularProgressIndicator()
              : ElevatedButton(
                  onPressed: _handleLogin,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    minimumSize: Size(double.infinity, 50),
                  ),
                  child: Text("ĐĂNG NHẬP", style: TextStyle(color: Colors.white)),
                ),
          ],
        ),
      ),
    );
  }
}