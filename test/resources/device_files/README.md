# KNX Device Test Files

## ⚠️ Important Notice

This directory is intentionally empty in the repository to avoid copyright and licensing issues.

## 📋 About KNX Device Files

KNX device configuration files (.knxprod) are proprietary files that contain:
- Device-specific configurations
- Parameter definitions
- Manufacturer intellectual property
- Copyrighted content

## 🔗 Obtaining Test Files

To run the full test suite, you need to obtain KNX device files from:

**MDT Devices:**
https://www.mdt-group.com/for-professionals/downloads/ets-product-data.html

**Other Manufacturers:**
Check the manufacturer's website for ETS product downloads

## 📁 Recommended Test Files

For comprehensive testing, consider obtaining:

1. **MDT_KP_EZ_01_Energy_Meter_V11.knxprod** - Energy meter device
2. **MDT_KP_AKU_03_Universal_Actuator_V41a.knxprod** - Universal actuator
3. **SCN-DA64x-04_MDT_KP_V40a.knxprod** - Other device type

## 📂 Directory Structure

```
test/resources/device_files/
├── MDT_KP_EZ_01_Energy_Meter_V11.knxprod      # Optional
├── MDT_KP_AKU_03_Universal_Actuator_V41a.knxprod # Optional
├── SCN-DA64x-04_MDT_KP_V40a.knxprod           # Optional
└── README.md                                  # This file
```

## 🚀 Alternative: Mock Files

If you cannot obtain real device files, consider:
1. Using mock files with synthetic data
2. Creating minimal test files for basic testing
3. Using only the tests that don't require device files

## ✅ Best Practices

1. **Do not commit proprietary files** to public repositories
2. **Document the source** of any test files used
3. **Respect copyright** and licensing terms
4. **Consider open alternatives** for basic testing

## 📝 Notes

- Device files are typically obtained through ETS (Engineering Tool Software)
- Manufacturers may have specific terms for using their device files
- Always check the manufacturer's website for the latest versions
- Consider contacting manufacturers for test/ evaluation licenses

## 🔧 Test Configuration

If you add device files to this directory:
1. Ensure you have the right to use them
2. Document the source and license
3. Consider adding to .gitignore
4. Update tests as needed

The tests will automatically detect and use any device files present in this directory.