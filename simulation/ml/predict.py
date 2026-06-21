"""
ML Prediction — Predictive Cooling
=====================================
Loads the trained model and predicts future supply temperature.
If predicted temp exceeds threshold, recommends preemptive pump increase.

Usage:
  python simulation/ml/predict.py --gpu-power 400 --ambient 30 --pump 60 --valve 50
"""

import os
import sys
import pickle
import json
from dataclasses import dataclass

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, project_root)


@dataclass
class PredictionResult:
    """Result of a predictive cooling assessment."""
    predicted_supply_temp_c: float
    current_supply_temp_c: float
    threshold_c: float
    exceeds_threshold: bool
    recommended_pump_increase_pct: float
    confidence: str  # "high", "medium", "low"
    horizon_s: int


class PredictiveCooling:
    """
    Predictive cooling controller.
    Loads trained model and provides preemptive recommendations.
    """

    def __init__(self, model_path: str = None, threshold_c: float = 40.0):
        """
        Args:
            model_path: Path to trained model .pkl file
            threshold_c: Supply temp threshold for preemptive action
        """
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'models', 'cooling_predictor.pkl'
            )

        self.model_path = model_path
        self.threshold_c = threshold_c
        self.model = None
        self.metadata = None

        self._load_model()

    def _load_model(self):
        """Load the trained model from disk."""
        if not os.path.exists(self.model_path):
            print(f"  WARNING: Model not found at {self.model_path}")
            print(f"  Run 'python simulation/ml/train_model.py' first.")
            return

        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)

        # Load metadata if available
        meta_path = self.model_path.replace('.pkl', '_metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                self.metadata = json.load(f)

    def predict(self, gpu_power_kw: float, ambient_temp_c: float,
                pump_speed_pct: float, valve_position_pct: float,
                current_supply_temp_c: float = 35.0) -> PredictionResult:
        """
        Predict supply temperature 60 seconds in the future.
        
        Args:
            gpu_power_kw: Current GPU total power [kW]
            ambient_temp_c: Current ambient temperature [°C]
            pump_speed_pct: Current pump speed [%]
            valve_position_pct: Current valve position [%]
            current_supply_temp_c: Current supply temp for reference
            
        Returns:
            PredictionResult with recommendation
        """
        if self.model is None:
            # Fallback: simple heuristic when model not available
            predicted = current_supply_temp_c + (gpu_power_kw - 200) * 0.01
            return PredictionResult(
                predicted_supply_temp_c=round(predicted, 2),
                current_supply_temp_c=current_supply_temp_c,
                threshold_c=self.threshold_c,
                exceeds_threshold=predicted > self.threshold_c,
                recommended_pump_increase_pct=10.0 if predicted > self.threshold_c else 0.0,
                confidence="low",
                horizon_s=60,
            )

        import numpy as np
        features = np.array([[gpu_power_kw, ambient_temp_c, pump_speed_pct, valve_position_pct]])
        predicted = float(self.model.predict(features)[0])

        # Determine confidence based on model metadata
        confidence = "medium"
        if self.metadata:
            r2 = self.metadata.get('test_r2', 0)
            if r2 > 0.9:
                confidence = "high"
            elif r2 < 0.7:
                confidence = "low"

        # Calculate recommended pump increase
        exceeds = predicted > self.threshold_c
        pump_increase = 0.0
        if exceeds:
            # Proportional increase: ~5% per °C above threshold
            overshoot = predicted - self.threshold_c
            pump_increase = min(30.0, overshoot * 5.0)

        return PredictionResult(
            predicted_supply_temp_c=round(predicted, 2),
            current_supply_temp_c=current_supply_temp_c,
            threshold_c=self.threshold_c,
            exceeds_threshold=exceeds,
            recommended_pump_increase_pct=round(pump_increase, 1),
            confidence=confidence,
            horizon_s=60,
        )


def main():
    """CLI for predictive cooling."""
    import argparse

    parser = argparse.ArgumentParser(description="Predictive Cooling Model")
    parser.add_argument("--gpu-power", type=float, default=400.0,
                       help="GPU total power [kW]")
    parser.add_argument("--ambient", type=float, default=25.0,
                       help="Ambient temperature [°C]")
    parser.add_argument("--pump", type=float, default=60.0,
                       help="Current pump speed [%%]")
    parser.add_argument("--valve", type=float, default=50.0,
                       help="Current valve position [%%]")
    parser.add_argument("--supply-temp", type=float, default=35.0,
                       help="Current supply temperature [°C]")
    parser.add_argument("--threshold", type=float, default=40.0,
                       help="Supply temp warning threshold [°C]")
    args = parser.parse_args()

    predictor = PredictiveCooling(threshold_c=args.threshold)

    result = predictor.predict(
        gpu_power_kw=args.gpu_power,
        ambient_temp_c=args.ambient,
        pump_speed_pct=args.pump,
        valve_position_pct=args.valve,
        current_supply_temp_c=args.supply_temp,
    )

    print()
    print("  Predictive Cooling Assessment")
    print("  " + "=" * 40)
    print(f"  Current supply temp:    {result.current_supply_temp_c:.1f} °C")
    print(f"  Predicted (t+{result.horizon_s}s):   {result.predicted_supply_temp_c:.1f} °C")
    print(f"  Threshold:              {result.threshold_c:.1f} °C")
    print(f"  Confidence:             {result.confidence}")
    print()

    if result.exceeds_threshold:
        print(f"  ⚠️  WARNING: Predicted temp exceeds threshold!")
        print(f"  💡 Recommendation: Increase pump speed by "
              f"{result.recommended_pump_increase_pct:.1f}%")
    else:
        print(f"  ✅ Supply temp within safe range")
    print()


if __name__ == "__main__":
    main()
