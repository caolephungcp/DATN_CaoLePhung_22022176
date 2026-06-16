import 'package:flutter/material.dart';

import 'dart:async';
import '../services/iot_service.dart';
import '../models/app_notification.dart';

class HomeView extends StatefulWidget {
  @override
  _HomeViewState createState() => _HomeViewState();
}

class _HomeViewState extends State<HomeView> {
  final IotService _iotService = IotService();
  Timer? _timer;
  
  // Các biến lưu giá trị thực tế
  String temp1 = "__";
  String soil1 = "__";
  String anhSang = "__";
  String ph1 = "__";
  String soil2 = "__";
  String temp2 = "__";
  String ph2 = "__";

  int at1 = 1; // Giai đoạn cây ngô ruộng 1
  int at2 = 1; // Giai đoạn cây ngô ruộng 2

  String weatherDesc = "Đang cập nhật";
  double weatherTemp = 0.0;
  int weatherHumidity = 0;
  int weatherPop = 0;
  String weatherMain = "";
  int weatherClouds = 0;
  double weatherRain3h = 0.0;

  final List<String> cropStates = [
    "Giai đoạn 1",
    "Giai đoạn 2",
    "Giai đoạn 3",
    "Giai đoạn 4",
    "Giai đoạn 5"
  ];

  // Trạng thái các máy bơm (sau này sẽ lấy từ ThingsBoard)
  Map<String, bool> pumpStates = {
    "F1_P1": false,
    "F1_P2": true,
    "F2_P1": false,
  };

  Map<String, bool> isAutoMode = {
    "RUỘNG NGÔ 1": false,
    "RUỘNG NGÔ 2": false,
  };

  @override
  void initState() {
    super.initState();
    _fetchRealData(); // Lấy dữ liệu lần đầu
    // Thiết lập tự động lấy dữ liệu sau mỗi 5 giây
    _timer = Timer.periodic(Duration(seconds: 5), (timer) => _fetchRealData());
  }

  @override
  void dispose() {
    _timer?.cancel(); // Quan trọng: Hủy timer khi thoát trang để tránh tốn pin/ram
    super.dispose();
  }

  Future<void> _fetchRealData() async {
    final String deviceId = "657b4290-2426-11f1-afd7-eb430bfb427f";

    // Gọi song song cả 2 API để tối ưu tốc độ
    final results = await Future.wait([
      _iotService.getLatestTelemetry(deviceId),
      _iotService.getAttributes(deviceId), 
    ]);

    final telemetryData = results[0];
    final attributeData = results[1];

    setState(() {
      // --- 1. LẤY DỮ LIỆU CẢM BIẾN (Từ Telemetry) ---
      if (telemetryData.isNotEmpty) {
        soil1 = telemetryData['soil1']?[0]['value'].toString() ?? '__';
        temp1 = telemetryData['temp1']?[0]['value'].toString() ?? '__';
        ph1 = telemetryData['ph1']?[0]['value'].toString() ?? '__';
        anhSang = telemetryData['light']?[0]['value'].toString() ?? '__';

        soil2 = telemetryData['soil2']?[0]['value'].toString() ?? '__';
        temp2 = telemetryData['temp2']?[0]['value'].toString() ?? '__';
        ph2 = telemetryData['ph2']?[0]['value'].toString() ?? '__';
      }

      // --- 2. LẤY TRẠNG THÁI ĐIỀU KHIỂN (Từ Shared Attributes) ---
      if (attributeData.isNotEmpty) {
        // Lưu ý: Cấu trúc Attribute trả về thường là Map phẳng: {"key": "value"}
        // Không có mảng [0]['value'] như Telemetry
        
        // Trạng thái Bơm
        pumpStates["F1_P1"] = _parseBool(attributeData['F1_P1']);
        pumpStates["F1_P2"] = _parseBool(attributeData['F1_P2']);
        pumpStates["F2_P1"] = _parseBool(attributeData['F2_P1']);

        // Trạng thái Chế độ (Tự động/Thủ công)
        isAutoMode["RUỘNG NGÔ 1"] = _parseBool(attributeData['F1']);
        isAutoMode["RUỘNG NGÔ 2"] = _parseBool(attributeData['F2']);

        // Trạng thái Giai đoạn cây ngô (AT)
        at1 = int.tryParse(attributeData['AT1']?.toString() ?? '1') ?? 1;
        at2 = int.tryParse(attributeData['AT2']?.toString() ?? '1') ?? 1;

        weatherDesc = attributeData['weather_desc']?.toString() ?? "Đang cập nhật";
        weatherTemp = double.tryParse(attributeData['weather_temp']?.toString() ?? '0') ?? 0.0;
        weatherHumidity = int.tryParse(attributeData['weather_humidity']?.toString() ?? '0') ?? 0;
        weatherPop = int.tryParse(attributeData['weather_pop']?.toString() ?? '0') ?? 0;
        weatherMain = attributeData['weather_main']?.toString() ?? "";
        weatherClouds = int.tryParse(attributeData['weather_clouds']?.toString() ?? '0') ?? 0;
        
        // Lượng mưa dự báo 3h (nếu có)
        weatherRain3h = double.tryParse(attributeData['weather_rain_3h']?.toString() ?? '0') ?? 0.0;
      }
    });
  }

  bool _parseBool(dynamic value) {
    if (value == null) return false;
    if (value is bool) return value;
    return value.toString().toLowerCase() == "true" || value.toString() == "1";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFFF0F2F5),
      body: ListView( // Dùng ListView để cuộn toàn bộ trang
        padding: EdgeInsets.all(12),
        children: [
          _buildWeatherSection(),
          SizedBox(height: 20),
          
          // RUỘNG NGÔ SỐ 1
          _buildFarmSection(
            farmName: "RUỘNG NGÔ 1",
            sensors: [
              {"title": "Độ ẩm đất", "value": soil1, "icon": Icons.water_drop, "color": Colors.blue},
              {"title": "Nhiệt độ", "value": temp1, "icon": Icons.thermostat, "color": Colors.orange},
              {"title": "Độ pH", "value": ph1, "icon": Icons.science, "color": Colors.green},
            ],
            pumps: [
              {"id": "F1_P1", "name": "Máy bơm chính"},
              {"id": "F1_P2", "name": "Bơm phun sương"},
            ],
          ),

          SizedBox(height: 20),

          // RUỘNG NGÔ SỐ 2
          _buildFarmSection(
            farmName: "RUỘNG NGÔ 2",
            sensors: [
              {"title": "Độ ẩm đất", "value": soil2, "icon": Icons.water_drop, "color": Colors.blue},
              {"title": "Nhiệt độ", "value": temp2, "icon": Icons.thermostat, "color": Colors.orange},
              {"title": "Độ pH", "value": ph2, "icon": Icons.science, "color": Colors.green},
            ],
            pumps: [
              {"id": "F2_P1", "name": "Máy bơm tưới gốc"},
            ],
          ),
        ],
      ),
    );
  }

  // --- WIDGET XÂY DỰNG TỪNG PHÂN KHU RUỘNG ---
  Widget _buildFarmSection({
    required String farmName,
    required List<Map<String, dynamic>> sensors,
    required List<Map<String, dynamic>> pumps,
  }) {
    // Lấy trạng thái chế độ hiện tại của ruộng này
    bool auto = isAutoMode[farmName] ?? false;

    bool isField1 = farmName == "RUỘNG NGÔ 1";
    int currentAtValue = isField1 ? at1 : at2; // Giả sử bạn đã khai báo biến at1, at2 trong State
    String atKey = isField1 ? 'AT1' : 'AT2';
    String modeKey = isField1 ? 'F1' : 'F2';

    return Container(
      margin: EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // HEADER CỦA RUỘNG
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: auto ? Colors.blue.shade50 : Colors.green.shade50,
              borderRadius: BorderRadius.only(topLeft: Radius.circular(15), topRight: Radius.circular(15)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.grass, color: auto ? Colors.blue : Colors.green, size: 20),
                    SizedBox(width: 8),
                    Text(farmName, style: TextStyle(fontWeight: FontWeight.bold, color: auto ? Colors.blue.shade800 : Colors.green.shade800)),
                  ],
                ),
                
                // PHẦN ĐIỀU KHIỂN (State cây & Chế độ)
                Row(
                  children: [
                    // BẢNG CHỌN TRẠNG THÁI CÂY NGÔ (AT1/AT2)
                    Container(
                      height: 30,
                      margin: EdgeInsets.only(right: 8),
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: auto ? Colors.blue.shade200 : Colors.green.shade200),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<int>(
                          value: currentAtValue,
                          items: [1, 2, 3, 4, 5].map((int value) {
                            return DropdownMenuItem<int>(
                              value: value,
                              child: Text("GĐ $value", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                            );
                          }).toList(),
                          onChanged: (newValue) async {
                            if (newValue != null) {
                              setState(() {
                                if (isField1) at1 = newValue; else at2 = newValue;
                              });
                              // GỬI LÊN SERVER SHARED ATTRIBUTE
                              await _iotService.updateSharedAttributes({atKey: newValue});
                            }
                          },
                        ),
                      ),
                    ),

                    // NÚT CHUYỂN CHẾ ĐỘ THÔNG MINH / THỦ CÔNG
                    ActionChip(
                      avatar: Icon(auto ? Icons.psychology : Icons.touch_app, size: 14, color: Colors.white),
                      label: Text(auto ? "TỰ ĐỘNG" : "THỦ CÔNG", style: TextStyle(fontSize: 10, color: Colors.white)),
                      backgroundColor: auto ? Colors.blue : Colors.orange,
                      onPressed: () async {
                        bool newMode = !auto;
                        setState(() {
                          isAutoMode[farmName] = newMode;
                        });

                        // GỬI LÊN SERVER (Key F1 hoặc F2)
                        print("$farmName: ${newMode ? true : false}");
                        bool success = await _iotService.updateSharedAttributes({modeKey: newMode ? true : false});
                        
                        if (success) {
                          final newNoti = AppNotification(
                            title: newMode ? "$farmName - Chế độ: Thông minh" : "$farmName - Chế độ: Thủ công",
                            message: "Đã chuyển $farmName sang chế độ ${newMode ? 'Thông minh' : 'Thủ công'}.",
                            time: DateTime.now(),
                            type: 'mode',
                          );
                          globalNotifications.value = [newNoti, ...globalNotifications.value];
                        } else {
                          // Nếu cập nhật thất bại, hãy gạt lại chế độ trên UI
                          setState(() {
                            isAutoMode[farmName] = !newMode;
                          });
                          // Hiển thị thông báo lỗi nếu muốn
                        }                    
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),

          // PHẦN CẢM BIẾN
          Padding(
            padding: EdgeInsets.all(12),
            child: GridView.builder(
              shrinkWrap: true,
              physics: NeverScrollableScrollPhysics(),
              itemCount: sensors.length,
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
                childAspectRatio: 1.1,
              ),
              itemBuilder: (context, index) {
                return _buildTinySensorCard(
                  sensors[index]['title'],
                  sensors[index]['value'],
                  sensors[index]['icon'],
                  sensors[index]['color'],
                );
              },
            ),
          ),

          Divider(height: 1),

          // PHẦN ĐIỀU KHIỂN MÁY BƠM
          Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Column(
              children: pumps.map((pump) => _buildPumpTile(pump['id'], pump['name'], auto)).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTinySensorCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Color(0xFFF8F9FA),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 18),
          Text(title, style: TextStyle(fontSize: 9, color: Colors.grey[600]), overflow: TextOverflow.ellipsis),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  // Widget dòng điều khiển máy bơm
  Widget _buildPumpTile(String id, String name, bool isAuto) {
    bool isOn = pumpStates[id] ?? false;
    
    return Opacity(
      opacity: isAuto ? 0.8 : 1.0, // Làm mờ 50% nếu đang ở chế độ thông minh
      child: ListTile(
        dense: true,
        leading: Icon(Icons.settings_input_component, color: isOn ? Colors.green : Colors.grey, size: 20),
        title: Text(name, style: TextStyle(fontSize: 14)),
        subtitle: isAuto ? Text("AI đang điều khiển", style: TextStyle(fontSize: 10, color: Colors.blue)) : null,
        trailing: Transform.scale(
          scale: 0.8,
          child: Switch(
            value: isOn,
            // NẾU isAuto LÀ TRUE THÌ TRUYỀN NULL ĐỂ KHÓA NÚT
            onChanged: isAuto ? null : (val) async {
              // 1. Tạm thời đổi trạng thái trên UI cho mượt
              setState(() {
                pumpStates[id] = val;
              });

              // 2. Gọi lệnh 
              bool success = await _iotService.updateSharedAttributes({id: val});
              // 3. Nếu gửi lệnh thất bại (lỗi mạng), hãy gạt nút trở lại
              if (!success) {
                setState(() {
                  pumpStates[id] = !val;
                });
                // Hiển thị thông báo lỗi nếu muốn
              } else {
                final newNoti = AppNotification(
                  title: val ? "$id - Bật bơm" : "$id - Tắt bơm",
                  message: "Đã chuyển $id sang chế độ ${val ? 'Bật' : 'Tắt'}.",
                  time: DateTime.now(),
                  type: 'mode',
                );
                globalNotifications.value = [newNoti, ...globalNotifications.value];
              }

            },
            activeColor: Colors.green,
          ),
        ),
      ),
    );
  }

  Widget _buildWeatherSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.green.shade700, Colors.green.shade400],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          // --- Phần 1: Trạng thái chính ---
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Trạm quan trắc Hà Nội",
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    "${weatherDesc[0].toUpperCase()}${weatherDesc.substring(1)} - ${weatherTemp.toStringAsFixed(1)}°C",
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              _getWeatherIcon(weatherMain),
            ],
          ),
          
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Divider(color: Colors.white24, height: 1),
          ),

          // --- Phần 2: Các chỉ số chi tiết cho nông nghiệp ---
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildWeatherDetailItem(
                Icons.water_drop, 
                "Độ ẩm", 
                "$weatherHumidity%"
              ),
              _buildWeatherDetailItem(
                Icons.umbrella, 
                "Sắp mưa", 
                "$weatherPop%"
              ),
              _buildWeatherDetailItem(
                Icons.cloud, 
                "Lượng mưa", 
                "${weatherRain3h.toStringAsFixed(1)}mm"
              ),
            ],
          ),
        ],
      ),
    );
  }

  // Widget con hiển thị từng ô chỉ số
  Widget _buildWeatherDetailItem(IconData icon, String label, String value) {
    return Column(
      children: [
        Icon(icon, color: Colors.white70, size: 18),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(color: Colors.white70, fontSize: 10),
        ),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  // Hàm chọn Icon thông minh dựa trên weatherMain
  Widget _getWeatherIcon(String main) {
    IconData iconData;
    switch (main.toLowerCase()) {
      case 'clouds':
        iconData = Icons.cloud;
        break;
      case 'rain':
        iconData = Icons.beach_access; // Icon hình cái ô cho mưa
        break;
      case 'clear':
        iconData = Icons.wb_sunny;
        break;
      case 'thunderstorm':
        iconData = Icons.bolt;
        break;
      default:
        iconData = Icons.wb_cloudy_outlined;
    }
    return Icon(iconData, color: Colors.white, size: 40);
  }
}