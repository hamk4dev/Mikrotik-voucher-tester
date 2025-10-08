# MikroTik HotSpot Voucher Generator

A professional and efficient voucher generation system for MikroTik HotSpot with support for multiple export formats, flexible customization, and guaranteed unique voucher codes.

---

## Features

- Unique & Secure Codes - Guaranteed unique voucher generation
· Multiple Prefix Modes - Flexible prefix customization options
- Customizable Parameters - Adjust length, quantity, and validity
- Bandwidth Control - Configurable download/upload limits
- Multiple Export Formats - TXT, CSV, JSON, MikroTik Script
- Price Tracking - Built-in price management for paid vouchers
- Batch Generation - Efficient bulk creation with uniqueness assurance

---

## Installation

### Requirements

· Python 3.6+ installed on your system

Setup

1. Download the script file:
   ```
   voucher_generator.py
   ```
2. No external dependencies required — uses only Python's standard library

---

## Quick Start

Basic Usage

Run the script with default settings:

```bash
python voucher_generator.py
```

Default Settings Generate:

```
- 100 vouchers
- 8-character length with "VIP" prefix
- 24-hour validity
- 20M/10M bandwidth limit
- $5.00 price per voucher
- Multiple export formats: TXT, CSV, and JSON
```


---

## Custom Configuration

Edit the config dictionary in the main() function:

```python
config = {
    "quantity": 200,                     # Number of vouchers
    "length": 6,                         # Voucher code length
    "prefix_mode": PrefixMode.FIXED,     # Prefix mode type
    "prefix": "FREE",                    # Fixed prefix text
    "validity_hours": 48,                # Hours until expiry
    "bandwidth_limit": "50M/20M",        # Download/Upload speed
    "price": 10.00,                      # Price per voucher
    "output_formats": [
        OutputFormat.TXT,
        OutputFormat.MIKROTIK_SCRIPT
    ]
}
```

---

## Prefix Modes

Mode Description Example:
```
- FIXED Uses a constant prefix VIP1234

- RANDOM_LETTER Random uppercase letter prefix A1234, B5678

- RANDOM_DIGIT Random digit prefix 1ABCD, 2EFGH

- RANDOM_ALPHANUMERIC Random letter or digit prefix K9X12, 3D7AB
NONE No prefix, fully random code AB12CD34
```
---

## Output Formats

1. Text (.txt)

 - Simple list of voucher codes
 - Ideal for printing or manual distribution


2. CSV (.csv)

Structured data with complete voucher information:

 - Voucher code
 - Prefix
 - Length
 - Expiry date
 - Validity (hours) 
 - Bandwidth limit
 - Price
 - Generation timestamp

3. JSON (.json)

 - Full structured dataset
 - Suitable for external system integration

4. MikroTik Script (.rsc)

Auto-generated import script:

```
/ip hotspot user add name="VIP12345" password="VIP12345" limit-uptime=86400 comment="Auto-generated voucher"
```

---

## Advanced Usage

Programmatic Integration

```python
from voucher_generator import VoucherGeneratorPro, PrefixMode, OutputFormat

# Create generator instance
generator = VoucherGeneratorPro(
    prefix="CORP",
    length=8,
    prefix_mode=PrefixMode.FIXED,
    quantity=50,
    validity_hours=72,
    bandwidth_limit="100M/50M",
    price=15.00
)

# Generate vouchers
vouchers = generator.generate_batch()

Export to desired format
generator.export_vouchers(vouchers, "corporate_vouchers", OutputFormat.CSV)
```

Custom Character Pool

Modify the character pool in the __init__ method if needed:

```python
self.character_pool = string.ascii_uppercase + string.digits  # Default: A–Z and 0–9
```

---

## MikroTik Integration

Method 1: Script Import (Recommended)

1. Generate vouchers in MikroTik Script (.rsc) format
2. Login to your MikroTik router
3. Navigate to System → Scripts and paste the script
4. Or run via terminal:
   ```
   /import voucher_script.rsc
   ```

Method 2: Manual Entry

1. Export vouchers as TXT format
2. Copy voucher codes
3. Manually add in MikroTik:
   ```
   /ip hotspot user add name="CODE" password="CODE" limit-uptime=SECONDS
   ```

---

## Troubleshooting

### Common Issues & Solutions

Issue Cause / Solution
Duplicate vouchers System auto-prevents duplicates; increase length if needed
Prefix too long Ensure prefix length ≤ total voucher length
Memory issue Generate in smaller batches
Import error (.rsc) Check script format or HotSpot configuration

### Error Messages Guide

- "Could not generate unique voucher" → Increase voucher length or adjust prefix
- "Prefix is longer than total voucher length" → Shorten prefix or extend total length
- "Quantity must be positive" → Verify configuration parameters

---

## File Structure

Generated files follow this naming pattern:

```
voucher_batch_YYYYMMDD_HHMMSS.txt     # Plain voucher list
voucher_batch_YYYYMMDD_HHMMSS.csv     # Structured data
voucher_batch_YYYYMMDD_HHMMSS.json    # JSON data with metadata
voucher_batch_YYYYMMDD_HHMMSS.rsc     # MikroTik import script
```

---

## Support

For assistance or feature requests:

- Refer to the script documentation
- Consult MikroTik official HotSpot resources

---

## License

This script is provided as-is for use with MikroTik HotSpot management systems. Use responsibly and test thoroughly before deployment in production environments.

---

⚠️ Important Note: Always test generated vouchers in a safe environment before applying them to a live MikroTik router.
