import 'package:flutter/material.dart';
import '../../../../app/theme.dart';

class BookingStepIndicator extends StatelessWidget {
  const BookingStepIndicator({
    required this.steps,
    required this.currentStep,
    super.key,
  });

  final List<String> steps;
  final int currentStep;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 8),
    child: Row(
      children: [
        for (var i = 0; i < steps.length; i++) ...[
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: i < currentStep
                            ? brandNavy
                            : i == currentStep
                                ? brandCoral
                                : appBorder,
                        shape: BoxShape.circle,
                      ),
                      alignment: Alignment.center,
                      child: i < currentStep
                          ? const Icon(Icons.check, size: 16, color: Colors.white)
                          : Text(
                              '${i + 1}',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w800,
                                color: i == currentStep ? Colors.white : appMuted,
                              ),
                            ),
                    ),
                    if (i < steps.length - 1)
                      Expanded(
                        child: Container(
                          height: 2,
                          color: i < currentStep ? brandNavy : appBorder,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  steps[i],
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: i == currentStep ? FontWeight.w800 : FontWeight.w600,
                    color: i <= currentStep ? brandNavy : appMuted,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
          if (i < steps.length - 1) const SizedBox(width: 4),
        ],
      ],
    ),
  );
}
