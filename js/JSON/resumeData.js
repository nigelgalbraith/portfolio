// js/JSON/resumeData.js
// Contains structured resume data for dynamic injection.

const resumeData = {
  professionalOutline: `My career has taken me through a variety of roles, giving me both hands-on operational experience and exposure to management responsibilities. This mix has shown me that effective solutions need to balance practical realities with broader objectives. It’s also reinforced the importance of clear communication and a willingness to adapt, as the best outcomes often come from considering ideas and perspectives beyond your own.`,
  
  experience: [
    {
      company: "Tait Communications",
      location: "Christchurch",
      role: "Support Analyst",
      date: "Jan 2025 – Feb 2025",
      outline: [
        "Gained exposure to frontline monitoring and incident management in a 24/7 managed services environment.",
        "Adapted quickly to an access-restricted setting during a transitional period for the team."
      ],
      achievements: [
        "Built early familiarity with Tait’s internal monitoring and ITSM systems while assisting in live network support.",
        "Shadowed senior analysts to observe problem investigations and root cause analysis workflows.",
        "Demonstrated reliability and professionalism, earning the trust of team members in a short time."
      ]
    },
    {
      company: "Ara Institute of Canterbury",
      location: "Christchurch",
      role: "Student",
      date: "Jun 2021 – Nov 2024",
      outline: [
        "Completed a degree in Information and Communication Technologies, networking pathway."
      ],
      achievements: [
        "Capstone project providing an Ubuntu KVM solution to replace VMware Workstation Pro.",
        "Goal was cost-effective licensing, improved resource flexibility, and maximize open-source learning support across Ara's virtual machine labs.",
        "Project showed adaptability of Ubuntu and opened doors for alternative solutions in line with these goals."
      ]
    },
    {
      company: "Trade Staff",
      location: "Christchurch",
      role: "Joiner",
      date: "Jun 2016 – Feb 2019",
      outline: [
        "Construction of various kitchen furniture projects for individual and commercial clients.",
        "Learned new technology solutions within joinery, such as CNC machines, to produce products more efficiently."
      ],
      achievements: [
        "Gained understanding of design and process using CNC machines.",
        "Learned 3D design using AutoCAD and SketchUp for home DIY projects."
      ]
    },
    {
      company: "Downer",
      location: "Christchurch",
      role: "Traffic Management",
      date: "Jan 2009 – Jun 2016",
      outline: [
        "Establishing and disestablishing traffic management sites prior to the commencement of road works and management of site safety",
        "Managing sign hire between different departments within Downer",
        "Preparing a Traffic Management Plans for a customer while working within time constraints to meet deadlines",
        "Designing Traffic Management Plan production process to improve Traffic Management Plan efficiency"
      ],
      achievements: [
        "Developed a web-based SharePoint database to manage Traffic Management Plan production.",
        "Built a GPS phone app to track real-time site and equipment locations.",
        "Inspired to pursue further study in IT due to this exposure to technical problem-solving."
      ],
      subRoles: [
        {
          title: "Traffic Management Planner Team Leader",
          date: "Jan 2015 - Jun 2016",
          items: [
            "Improved Traffic Management Plan efficiency through process redesign.",
            "Created internal SharePoint site for plan tracking and production."
          ]
        },
        {
          title: "Traffic Management Planner",
          date: "May 2013 - Jan 2015",
          items: [
            "Created plans and liaised with clients under pressure and tight deadlines."
          ]
        },
        {
          title: "Traffic Management Store Man",
          date: "Jan 2013 - May 2013",
          items: [
            "Maintained interdepartmental equipment flow."
          ]
        },
        {
          title: "Traffic Controller",
          date: "Jan 2012 - Jan 2013",
          items: [
            "Set up and disassembled traffic sites for roadworks."
          ]
        }
      ]
    },
    {
      company: "Laptop Universe",
      location: "Christchurch",
      role: "Customer Service & Computer Technical Support",
      date: "Jan 2009 - Jan 2012",
      outline: [
        "Answered customer inquiries and provided IT support.",
        "Recommended hardware/software upgrades.",
        "Performed repair tasks: virus removal, part replacement, data transfers."
      ],
      achievements: [
        "Supported customers following the 2011 earthquake while the store was recovering."
      ]
    }
  ],

  qualifications: [
    {
      institution: "Ara Institute of Canterbury",
      date: "2021 - 2024",
      awards: [
        "Bachelor of ICT, Network Infrastructure, 2024 (Graduated with Distinction, Highly Commended Achievement Award)",
        "Diploma in Systems Administration, 2023",
        "Diploma in Information Technology, 2021"
      ]
    },
    {
      institution: "The Computer Power Institute",
      date: "2007 - 2008",
      awards: ["Diploma in Electronic Business, 2008"]
    },
    {
      institution: "Christchurch Polytechnic Institute of Technology",
      date: "2004 - 2005",
      awards: ["Cert. Joinery - Lv1 & Stair making, 2005"]
    },
    {
      institution: "University of Canterbury",
      date: "2000 - 2003",
      awards: ["Bachelor of Science, Statistics, 2003"]
    }
  ],

  resumeLinks: [
    {
      label: "Curriculum vitae",
      href: "files/NigelGalbraith-CV.pdf",
      icon: "images/icons/optimized/CV.png",
      alt: "Resume PDF"
    },
    {
      label: "Cover Letter",
      href: "files/NigelGalbraith-CoverLetter.pdf",
      icon: "images/icons/optimized/CoverLetter.png",
      alt: "Cover Letter PDF"
    }
  ]
};
