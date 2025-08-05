// js/iconRegistry.js

// Determine correct relative path for icons
const ICON_PATH_PREFIX = window.location.pathname.includes("/projects/") ? "../" : "";

// Define all icons with correct prefixed image paths
const ICON_REGISTRY = {
  "degree":           { "alt": "Degree",                  "label": "BICT",                     "src": ICON_PATH_PREFIX + "images/icons/optimized/degree.png" },
  "cert":             { "alt": "Certificate",             "label": "CCNA Certified",           "src": ICON_PATH_PREFIX + "images/icons/optimized/cert.png" },
  "cloud":            { "alt": "Cloud",                   "label": "Azure Fundamentals",       "src": ICON_PATH_PREFIX + "images/icons/optimized/Azurecloud.png" },
  "cloud":            { "alt": "Cloud",                   "label": "Cloud Tech",               "src": ICON_PATH_PREFIX + "images/icons/optimized/cloud.png" },
  "sharepoint":       { "alt": "SharePoint",              "label": "SharePoint",               "src": ICON_PATH_PREFIX + "images/icons/optimized/SharePoint.png" },
  "office365":        { "alt": "Office 365",              "label": "Office 365",               "src": ICON_PATH_PREFIX + "images/icons/optimized/Office365.png" },
  "ubuntu":           { "alt": "ubuntu",                  "label": "Ubuntu KVM",               "src": ICON_PATH_PREFIX + "images/icons/optimized/ubuntu.png" },
  "linux":            { "alt": "Linux",                   "label": "Linux & CLI Tools",        "src": ICON_PATH_PREFIX + "images/icons/optimized/linux.png" },
  "libvirt":          { "alt": "libvirt",                 "label": "Libvirt",                  "src": ICON_PATH_PREFIX + "images/icons/optimized/libvrt.png" },
  "network":          { "alt": "Networking",              "label": "Network Setup",            "src": ICON_PATH_PREFIX + "images/icons/optimized/network.png" },
  "qemu":             { "alt": "qemu",                    "label": "QEMU",                     "src": ICON_PATH_PREFIX + "images/icons/optimized/qemu.png" },
  "virtual":          { "alt": "Virtualization",          "label": "Virtualization & KVM",     "src": ICON_PATH_PREFIX + "images/icons/optimized/virtual.png" },
  "powerShell":       { "alt": "powerShell",              "label": "powerShell",               "src": ICON_PATH_PREFIX + "images/icons/optimized/powerShell.png" },
  "shell":            { "alt": "Shell Scripting",         "label": "Shell Scripting",          "src": ICON_PATH_PREFIX + "images/icons/optimized/programing.png" },
  "python":           { "alt": "Python",                  "label": "Python",                   "src": ICON_PATH_PREFIX + "images/icons/optimized/python.png" },
  "permissions":      { "alt": "Permissions",             "label": "Permissions",              "src": ICON_PATH_PREFIX + "images/icons/optimized/permissions.png" },
  "repair":           { "alt": "DIY",                     "label": "Electronics & DIY Fixes",  "src": ICON_PATH_PREFIX + "images/icons/optimized/repair.png" },
  "tools":            { "alt": "Tools",                   "label": "Power Tools & Safety",     "src": ICON_PATH_PREFIX + "images/icons/optimized/tools.png" },
  "woodwork":         { "alt": "Woodwork",                "label": "Joinery & Carpentry",      "src": ICON_PATH_PREFIX + "images/icons/optimized/woodwork.png" },
  "problem_solving":  { "alt": "Problem Solving",         "label": "Problem Solving",          "src": ICON_PATH_PREFIX + "images/icons/optimized/problem-solving.png" },
  "debugging":        { "alt": "Debugging",               "label": "Debugging",                "src": ICON_PATH_PREFIX + "images/icons/optimized/debugging.png" },
  "teamwork":         { "alt": "Teamwork",                "label": "Team Collaboration",       "src": ICON_PATH_PREFIX + "images/icons/optimized/teamwork.png" },
  "collaboration":    { "alt": "Collaboration & Testing", "label": "Collaboration & Testing",  "src": ICON_PATH_PREFIX + "images/icons/optimized/CollabTest.png" },
  "automation":       { "alt": "System Automation",       "label": "System Automation",        "src": ICON_PATH_PREFIX + "images/icons/optimized/automation.png" },
  "security":         { "alt": "Security Best Practices", "label": "Security Best Practices",  "src": ICON_PATH_PREFIX + "images/icons/optimized/degree.png" },
  "gps_tracking":     { "alt": "GPS Tracking",            "label": "GPS Tracking",             "src": ICON_PATH_PREFIX + "images/icons/optimized/gps_tracking.png" },
  "gps":              { "alt": "GPS Integration",         "label": "GPS Integration",          "src": ICON_PATH_PREFIX + "images/icons/optimized/gpsIntegration.png" },
  "user_experience":  { "alt": "User Experience",         "label": "User Experience Design",   "src": ICON_PATH_PREFIX + "images/icons/optimized/user_experience.png" },
  "SketchUp":         { "alt": "SketchUp",                "label": "SketchUp",                 "src": ICON_PATH_PREFIX + "images/icons/optimized/SketchupIcon.png" },
  "ThreeD_Design":    { "alt": "3D Design",               "label": "3D Design",                "src": ICON_PATH_PREFIX + "images/icons/optimized/3D_Design.png" }
};
