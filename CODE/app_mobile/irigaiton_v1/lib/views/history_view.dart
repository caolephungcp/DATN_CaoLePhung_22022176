// lib/views/history_view.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../services/iot_service.dart';

class HistoryView extends StatefulWidget {
  @override
  _HistoryViewState createState() => _HistoryViewState();
}

class _HistoryViewState extends State<HistoryView> {
  final IotService _iotService = IotService();
  List<Map<String, dynamic>> historyData = [];
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => isLoading = true);
    // Thay ID thiết bị DongNgo1 của bạn vào đây
    final data = await _iotService.getHistoryTelemetry("657b4290-2426-11f1-afd7-eb430bfb427f", 100);
    
    List<Map<String, dynamic>> tempHistory = [];
    if (data != null && data.containsKey('temp1')) {
      print("abc");
      print(data);
      var tempList = data['temp1'];
      var soilList = data['soil1'] ?? [];
      var phList = data['ph1'] ?? [];
      for (var i = 0; i < tempList.length; i++) {
        tempHistory.add({
          "index": i.toDouble(),
          "temp": double.tryParse(tempList[i]['value'].toString()) ?? 0.0,
          "soil": (i < soilList.length) ? (double.tryParse(soilList[i]['value'].toString()) ?? 0.0) : 0.0,
          "ph": (i < phList.length) ? (double.tryParse(phList[i]['value'].toString()) ?? 0.0) : 0.0,
          "time": DateFormat('HH:mm').format(DateTime.fromMillisecondsSinceEpoch(tempList[i]['ts'])),
        });
      }
    }
    setState(() {
      historyData = tempHistory.reversed.toList();
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Thống kê dữ liệu"), backgroundColor: Colors.green, elevation: 0),
      body: isLoading 
        ? Center(child: CircularProgressIndicator())
        : SingleChildScrollView( // Chống lỗi tràn màn hình (Vạch vàng đen)
            child: Column(
              children: [
                Container(
                  padding: EdgeInsets.all(16),
                  color: Colors.green.withOpacity(0.1),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildIndicator(Colors.red, "Nhiệt độ (°C)"),
                      _buildIndicator(Colors.blue, "Độ ẩm (%)"),
                      _buildIndicator(Colors.green, "pH"),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 30, right: 20, left: 10),
                  child: SizedBox(
                    height: 300, // Chiều cao cố định để không bị tràn
                    child: LineChart(
                      _mainChartData(),
                    ),
                  ),
                ),
                SizedBox(height: 20),
                // Thêm một cái bảng nhỏ liệt kê dữ liệu bên dưới cho chuyên nghiệp
                Text("Dữ liệu chi tiết", style: TextStyle(fontWeight: FontWeight.bold)),
                ListView.builder(
                  shrinkWrap: true,
                  physics: NeverScrollableScrollPhysics(),
                  itemCount: historyData.length,
                  itemBuilder: (context, index) {
                    final item = historyData[index];
                    return ListTile(
                      dense: true,
                      title: Text("Thời gian: ${item['time']}"),
                      trailing: Text("${item['temp']}°C - ${item['soil']}% - ${item['ph']}", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                    );
                  },
                )
              ],
            ),
          ),
    );
  }

  Widget _buildIndicator(Color color, String text) {
    return Row(children: [
      Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      SizedBox(width: 4),
      Text(text, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500))
    ]);
  }

  LineChartData _mainChartData() {
    return LineChartData(
      gridData: FlGridData(show: true, drawVerticalLine: false, getDrawingHorizontalLine: (value) => FlLine(color: Colors.grey.withOpacity(0.2), strokeWidth: 1)),
      titlesData: FlTitlesData(
        show: true,
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            getTitlesWidget: (value, meta) {
              int idx = value.toInt();
              return (idx >= 0 && idx < historyData.length) ? Text(historyData[idx]['time'], style: TextStyle(fontSize: 10)) : Text("");
            },
          ),
        ),
      ),
      borderData: FlBorderData(show: false),
      lineBarsData: [
        _generateLineData(Colors.red, 'temp'),
        _generateLineData(Colors.blue, 'soil'),
        _generateLineData(Colors.green, 'ph'),
      ],
    );
  }

  LineChartBarData _generateLineData(Color color, String key) {
    return LineChartBarData(
      spots: historyData.asMap().entries.map((e) => FlSpot(e.key.toDouble(), e.value[key])).toList(),
      isCurved: true,
      color: color,
      barWidth: 3,
      isStrokeCapRound: true,
      dotData: FlDotData(show: true),
      belowBarData: BarAreaData(show: true, color: color.withOpacity(0.1)),
    );
  }
}