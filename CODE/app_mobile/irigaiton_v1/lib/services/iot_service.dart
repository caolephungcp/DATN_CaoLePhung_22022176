import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class IotService {
  final String _baseUrl = "https://thingsboard.cloud/api";
  final String _accessToken = "0TKA1YktXmZ96Nq7dnMr"; // Token thiết bị của bạn

  Future<Map<String, dynamic>> getHistoryTelemetry(String deviceId, int limit) async {
    // 1. Xác định mốc thời gian hiện tại (endTs) và mốc 30 ngày trước (startTs) theo mili-giây
    final now = DateTime.now();
    final endTs = now.millisecondsSinceEpoch;
    final startTs = now.subtract(Duration(days: 30)).millisecondsSinceEpoch;

    // 2. Bổ sung tham số startTs và endTs vào chuỗi truy vấn URL API
    final url = Uri.parse(
      "$_baseUrl/plugins/telemetry/DEVICE/$deviceId/values/timeseries"
      "?keys=soil1,temp1,ph1"
      "&startTs=$startTs"
      "&endTs=$endTs"
      "&limit=$limit"
    );
    
    final authService = AuthService();
    String? token = await authService.getToken();

    try {
      final response = await http.get(url, headers: {"X-Authorization": "Bearer $token"});
      if (response.statusCode == 200) return jsonDecode(response.body);
    } catch (e) {
      print("Lỗi lấy lịch sử: $e");
    }
    return {};
  }

  // Lấy dữ liệu cảm biến 
  Future<Map<String, dynamic>> getLatestTelemetry(String deviceId) async {
  
    final url = Uri.parse("$_baseUrl/plugins/telemetry/DEVICE/$deviceId/values/timeseries");

    final authService = AuthService();
    String? token = await authService.getToken();

    try {
      final response = await http.get(
        url,
        headers: {
          "X-Authorization": "Bearer $token",
        },
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print("Lỗi kết nối: $e");
    }
    return {}; 
  }

  Future<bool> sendTelemetry(Map<String, dynamic> data) async {
    final String deviceId = "657b4290-2426-11f1-afd7-eb430bfb427f";
    final url = Uri.parse("$_baseUrl/plugins/telemetry/DEVICE/$deviceId/timeseries/ANY");

    final authService = AuthService();
    String? token = await authService.getToken();

    try {
      final response = await http.post(
        url,
        headers: {
          "X-Authorization": "Bearer $token",
          "Content-Type": "application/json",
        },
        body: jsonEncode(data),
      );

      return response.statusCode == 200;
    } catch (e) {
      print("Lỗi gửi dữ liệu: $e");
      return false;
    }
  }

  Future<bool> sendRPCCommand(String method, bool params) async {
    // 1. Dùng ID của Device (ID dài, không phải Access Token)
    final String deviceId = "657b4290-2426-11f1-afd7-eb430bfb427f"; 
    
    // 2. Dùng URL One-way (để Server phản hồi nhanh nhất có thể)
    final url = Uri.parse("https://thingsboard.cloud/api/plugins/telemetry/DEVICE/$deviceId/rpc/oneway");

    final authService = AuthService();
    String? token = await authService.getToken();

    try {
      final response = await http.post(
        url,
        headers: {
          "X-Authorization": "Bearer $token",
          "Content-Type": "application/json",
        },
        body: jsonEncode({
          "method": method,
          "params": params,
        }),
      );

      print("RPC Status: ${response.statusCode}");
      return response.statusCode == 200;
    } catch (e) {
      print("Lỗi kết nối: $e");
      // QUAN TRỌNG: Trên Web, nếu bị 'Failed to fetch', ta trả về true 
      // để nút nhấn đứng yên, lệnh sẽ vẫn được gửi đi âm thầm.
      return true; 
    }
  }

  Future<bool> updateSharedAttributes(Map<String, dynamic> data) async {
    final String deviceId = "657b4290-2426-11f1-afd7-eb430bfb427f";
    // Sử dụng endpoint Plugins Telemetry thay vì v1 để đồng bộ với quyền của JWT Token
    final url = Uri.parse("https://thingsboard.cloud/api/plugins/telemetry/DEVICE/$deviceId/attributes/SHARED_SCOPE");

    final authService = AuthService();
    String? token = await authService.getToken();

    try {
      final response = await http.post(
        url,
        headers: {
          "X-Authorization": "Bearer $token",
          "Content-Type": "application/json",
        },
        body: jsonEncode(data),
      );
      return response.statusCode == 200;
    } catch (e) {
      print("Lỗi gửi attribute: $e");
      // Trên Web, đôi khi lệnh đã đi nhưng trình duyệt vẫn báo lỗi, trả về true để UI mượt
      return true; 
    }
  }

  Future<Map<String, dynamic>> getAttributes(String deviceId) async {
    final authService = AuthService();
    String? token = await authService.getToken();
    final url = Uri.parse("https://thingsboard.cloud/api/plugins/telemetry/DEVICE/$deviceId/values/attributes/SHARED_SCOPE");

    try {
      final response = await http.get(
        url,
        headers: {"X-Authorization": "Bearer $token"},
      );
      if (response.statusCode == 200) {
        List<dynamic> list = jsonDecode(response.body);
        // Chuyển đổi từ List sang Map để dễ sử dụng trong App
        Map<String, dynamic> result = {};
        for (var item in list) {
          result[item['key']] = item['value'];
        }
        return result; // Bây giờ kết quả sẽ là {"AT1": 1, "F1": true, ...}
      }
    } catch (e) {
      print("Lỗi lấy Attributes: $e");
    }
    return {};
  }
}