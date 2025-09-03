# Release Notes - Version 0.2.6

## Advanced Orientation Light Controls for Sela Models

### New Features

#### Comprehensive Orientation Light Automation

- **Sensor-Dependent Activation**: Enable/disable automatic activation based on user presence
- **Ambient Light Dependency**: Configure light to activate only in dark conditions  
- **LED Override Control**: Manual override for always-on or always-off operation
- **Smart Follow-Up Time**: Configurable light run-on time (0-300 seconds) after user leaves

#### Advanced Sensor Configuration

- **Detection Distance Control**: Adjustable sensor range (0-10 levels)
- **Motion Sensor Sensitivity**: Fine-tune detection sensitivity (0-10 levels)
- **Movement Sensor Toggle**: Enable/disable movement detection entirely
- **Ambient Light Sensitivity**: Configure ambient light sensor responsiveness (0-10 levels)
- **Dark Threshold Setting**: Custom darkness activation level (0-100%)

#### Enhanced Device State Tracking

- Added 9 new orientation light state properties for comprehensive monitoring
- Real-time feedback for all sensor and automation settings
- Professional-grade lighting system status visibility

### Technical Improvements

#### Official Data Point Integration

All controls now use verified Geberit protocol data points:

| Feature | Data Point | Range | Description |
|---------|------------|-------|-------------|
| Sensor Activation | 45 | 0-1 | Motion-based control |
| Ambient Dependency | 46 | 0-1 | Light-level based activation |
| Manual Override | 47 | 0-1 | Force on/off control |
| Follow-Up Time | 50 | 0-300s | Run-on duration |
| Sensor Distance | 51 | 0-10 | Detection range |
| Sensor Sensitivity | 53 | 0-10 | Motion detection level |
| Movement Control | 55 | 0-1 | Enable/disable motion sensor |
| Ambient Sensitivity | 56 | 0-10 | Light sensor responsiveness |
| Dark Threshold | 58 | 0-100% | Activation darkness level |

#### Enhanced Feature Discovery

- Updated orientation light detection to test 13 comprehensive data points
- Robust feature availability checking for Sela model variations
- Automatic detection ensures only supported features are exposed

### Usage

Sela model users now have access to:

- **Professional lighting automation** with motion and ambient light detection
- **Granular sensor tuning** for optimal performance in different environments  
- **Flexible timing controls** for custom lighting behaviors
- **Manual override capabilities** for special situations
- **Complete Home Assistant integration** with real-time status monitoring

### Compatibility

- Maintains full backward compatibility with all previous versions
- No configuration changes required for existing installations
- Enhanced features automatically available for compatible Sela models
- Standard models continue to work with basic night light controls

### Installation

Update through HACS or manually replace the integration files. The advanced orientation light controls will automatically appear for Sela models that support these features.

## Breaking Changes

None. All existing functionality preserved and enhanced.

## Bug Fixes

- Improved orientation light feature detection accuracy
- Enhanced error handling for advanced sensor commands
- Better validation of sensor setting ranges
