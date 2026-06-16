import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/constants.dart';

class AuthService {
  // Hàm đăng nhập
  Future<bool> login(String email, String password) async {
    // Đảm bảo URL chính xác cho thingsboard.cloud
    final url = Uri.parse("https://thingsboard.cloud/api/auth/login");
    
    try {
      final response = await http.post(
        url,
        // QUAN TRỌNG: Phải có headers này để Server hiểu bạn đang gửi JSON
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        // Chuyển đổi Map sang chuỗi JSON
        body: jsonEncode({
          "username": email, 
          "password": password
        }),
      );

      print("Status code: ${response.statusCode}"); // Debug để xem mã lỗi

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        String token = data['token'];
        
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('token', token);
        
        return true; 
      } else {
        // Nếu lỗi 401: Sai email/pass. Nếu lỗi 403: Tài khoản bị khóa...
        print("Đăng nhập thất bại: ${response.body}");
        return false;
      }
    } catch (e) {
      print("Lỗi kết nối mạng: $e");
      return false;
    }
  }

  // Hàm kiểm tra xem đã đăng nhập chưa
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  // Hàm đăng xuất
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
  }
}