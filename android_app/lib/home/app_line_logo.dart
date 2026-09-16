import 'package:flutter/material.dart';

class AppLineLogo extends StatelessWidget {
  const AppLineLogo({super.key, this.size = 38});

  final double size;

  @override
  Widget build(BuildContext context) => CustomPaint(
        size: Size.square(size),
        painter: _AppLineLogoPainter(Theme.of(context).colorScheme.primary),
      );
}

class _AppLineLogoPainter extends CustomPainter {
  const _AppLineLogoPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * .065
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final center = Offset(size.width * .5, size.height * .48);
    canvas.drawCircle(center, size.width * .31, paint);
    canvas.drawOval(
      Rect.fromCenter(center: center, width: size.width * .27, height: size.height * .62),
      paint,
    );
    canvas.drawLine(
      Offset(size.width * .2, center.dy),
      Offset(size.width * .8, center.dy),
      paint,
    );
    final book = Path()
      ..moveTo(size.width * .14, size.height * .72)
      ..quadraticBezierTo(size.width * .34, size.height * .65, size.width * .5, size.height * .78)
      ..quadraticBezierTo(size.width * .66, size.height * .65, size.width * .86, size.height * .72);
    canvas.drawPath(book, paint);
  }

  @override
  bool shouldRepaint(covariant _AppLineLogoPainter oldDelegate) => oldDelegate.color != color;
}
