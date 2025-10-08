"""
MikroTik HotSpot Voucher Generator
"""

import random
import string
import json
import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta
from enum import Enum
import secrets


class PrefixMode(Enum):
    FIXED = "fixed"
    RANDOM_LETTER = "random_letter"
    RANDOM_DIGIT = "random_digit"
    RANDOM_ALPHANUMERIC = "random_alphanumeric"
    NONE = "none"


class OutputFormat(Enum):
    TXT = "txt"
    CSV = "csv"
    JSON = "json"
    MIKROTIK_SCRIPT = "rsc"


class VoucherGeneratorPro:

    def __init__(self,
                 prefix: str = "J",
                 length: int = 7,
                 prefix_mode: PrefixMode = PrefixMode.FIXED,
                 quantity: int = 300,
                 validity_hours: int = 24,
                 bandwidth_limit: str = "10M/5M",
                 price: float = 0.0):

        self.prefix = prefix
        self.length = length
        self.prefix_mode = prefix_mode
        self.quantity = quantity
        self.validity_hours = validity_hours
        self.bandwidth_limit = bandwidth_limit
        self.price = price
        self.character_pool = string.ascii_uppercase + string.digits
        self.generated_vouchers = set()

    def _generate_prefix(self) -> str:
        if self.prefix_mode == PrefixMode.FIXED:
            return self.prefix
        elif self.prefix_mode == PrefixMode.RANDOM_LETTER:
            return secrets.choice(string.ascii_uppercase)
        elif self.prefix_mode == PrefixMode.RANDOM_DIGIT:
            return secrets.choice(string.digits)
        elif self.prefix_mode == PrefixMode.RANDOM_ALPHANUMERIC:
            return secrets.choice(string.ascii_uppercase + string.digits)
        elif self.prefix_mode == PrefixMode.NONE:
            return ""
        return self.prefix

    def _ensure_unique(self, voucher: str) -> str:
        max_attempts = 1000
        attempts = 0

        while voucher in self.generated_vouchers and attempts < max_attempts:
            actual_prefix = self._generate_prefix()
            random_length = self.length - len(actual_prefix)
            random_chars = ''.join(
                secrets.choice(self.character_pool)
                for _ in range(random_length)
            )
            voucher = f"{actual_prefix}{random_chars}"
            attempts += 1
        if attempts == max_attempts:
            raise RuntimeError("Could not generate unique voucher after maximum attempts")

        self.generated_vouchers.add(voucher)
        return voucher

    def generate_single_voucher(self) -> Dict[str, str]:

        actual_prefix = self._generate_prefix()
        random_length = self.length - len(actual_prefix)

        if random_length < 0:
            raise ValueError("Prefix is longer than total voucher length")

        random_chars = ''.join(
            secrets.choice(self.character_pool)
            for _ in range(random_length)
        )

        voucher_code = f"{actual_prefix}{random_chars}"
        voucher_code = self._ensure_unique(voucher_code)

        expiry_time = datetime.now() + timedelta(hours=self.validity_hours)

        return {
            "voucher_code": voucher_code,
            "prefix": actual_prefix,
            "length": self.length,
            "valid_until": expiry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "validity_hours": self.validity_hours,
            "bandwidth_limit": self.bandwidth_limit,
            "price": f"${self.price:.2f}" if self.price > 0 else "Free",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def generate_batch(self) -> List[Dict[str, str]]:

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

        return [self.generate_single_voucher() for _ in range(self.quantity)]

    def export_vouchers(self,
                       vouchers: List[Dict[str, str]],
                       filename: str = "vouchers",
                       format: OutputFormat = OutputFormat.TXT) -> str:
        file_path = Path(f"{filename}.{format.value}")
        try:
            if format == OutputFormat.TXT:
                self._export_txt(vouchers, file_path)
            elif format == OutputFormat.CSV:
                self._export_csv(vouchers, file_path)
            elif format == OutputFormat.JSON:
                self._export_json(vouchers, file_path)
            elif format == OutputFormat.MIKROTIK_SCRIPT:
                self._export_mikrotik_script(vouchers, file_path) 
            return str(file_path.absolute())

        except Exception as e:
            print(f"Export error: {e}")
            raise

    def _export_txt(self, vouchers: List[Dict[str, str]], file_path: Path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Voucher Batch - Generated: {datetime.now()}\n")
            f.write(f"Total: {len(vouchers)} vouchers\n")
            f.write(f"Validity: {self.validity_hours} hours\n")
            f.write("=" * 50 + "\n\n")

            for voucher in vouchers:
                f.write(f"{voucher['voucher_code']}\n")

    def _export_csv(self, vouchers: List[Dict[str, str]], file_path: Path):
        with open(file_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=vouchers[0].keys())
            writer.writeheader()
            writer.writerows(vouchers)

    def _export_json(self, vouchers: List[Dict[str, str]], file_path: Path):
        export_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_vouchers": len(vouchers),
                "validity_hours": self.validity_hours,
                "bandwidth_limit": self.bandwidth_limit
            },
            "vouchers": vouchers
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

    def _export_mikrotik_script(self, vouchers: List[Dict[str, str]], file_path: Path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("MikroTik HotSpot Voucher Script\n")
            f.write("Generated by Voucher Generator\n")
            f.write(f"Date: {datetime.now()}\n\n")

            for voucher in vouchers:
                f.write(f"/ip hotspot user add ")
                f.write(f"name=\"{voucher['voucher_code']}\" ")
                f.write(f"password=\"{voucher['voucher_code']}\" ")
                f.write(f"limit-uptime={self.validity_hours*3600} ")
                f.write(f"comment=\"Auto-generated voucher\"\n")

            f.write("\nScript execution complete\n")


def print_banner():

    banner = """
    MIKROTIK VOUCHER GENERATOR
    Professional Edition
    """
    print(banner)


def main():
    print_banner()

    config = {
        "quantity": 100,
        "length": 8,
        "prefix_mode": PrefixMode.FIXED,
        "prefix": "VIP",
        "validity_hours": 24,
        "bandwidth_limit": "20M/10M",
        "price": 5.00,
        "output_formats": [OutputFormat.TXT, OutputFormat.CSV, OutputFormat.JSON]
    }

    try:
        print("Generating professional vouchers...")
        print(f"Configuration: {config['quantity']} vouchers, {config['length']} chars")

        generator = VoucherGeneratorPro(
            prefix=config['prefix'],
            length=config['length'],
            prefix_mode=config['prefix_mode'],
            quantity=config['quantity'],
            validity_hours=config['validity_hours'],
            bandwidth_limit=config['bandwidth_limit'],
            price=config['price']
        )

        vouchers = generator.generate_batch()

        exported_files = []
        for format in config['output_formats']:
            filename = f"voucher_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            file_path = generator.export_vouchers(vouchers, filename, format)
            exported_files.append(file_path)

        print("\nGENERATION COMPLETE!")
        print(f"Generated: {len(vouchers)} vouchers")
        print(f"Files saved:")
        for file in exported_files:
            print(f"   {file}")

        print(f"\nSample vouchers:")
        for i, voucher in enumerate(vouchers[:5]):
            print(f"   {i+1}. {voucher['voucher_code']} "
                  f"(Expires: {voucher['valid_until']})")

        prefixes = [v['prefix'] for v in vouchers]
        unique_prefixes = set(prefixes)
        print(f"\nStatistics:")
        print(f"   Unique prefixes: {len(unique_prefixes)}")
        print(f"   Validity: {config['validity_hours']} hours")
        print(f"   Bandwidth: {config['bandwidth_limit']}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
