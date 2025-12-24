---
# Leave the homepage title empty to use the site title
title: ""
date: 2025-06-21
type: landing

design:
  # Default section spacing
  spacing: "2rem"

sections:
  - block: resume-biography-4
    content:
      # Choose a user profile to display (a folder name within `content/authors/`)
      username: admin
      text: ""
      # Show a call-to-action button under your biography? (optional)
      button:
        text: Download CV
        url: uploads/cv_dd_0625.pdf
    design:
      css_class: light
      background:
        color: light
        image:
          # Add your image background to `assets/media/`.
          filename: white.svg
          filters:
            brightness: 1.0
          size: cover
          position: center
          parallax: false
  - block: markdown-wide
    id: markmap
    content:
      title:
      text: |
       <style>
        .markmap{
            position: relative;
            user-select: none; /* Disable text selection */
        }
        .markmap > svg {
        width: 100%;
        height: 400px;
        }
        .markmap text {
          font-size: 30px !important;
        }
        </style>

        <div class="markmap" data-options='{"zoom": false, "pan": false}'>
        <script type="text/template">
        - My Research
          - Motivation
            - Digital Health Technologies
              - Objective Data
                - Physical Activity ⌚
                - Headband EEG 🎧
                - Continuous Glucose Monitor 🩸
                - Heart Rate ❤️
              - Subjective Data 
                - Ecological Momentary Assessment📱
            - Environmental Data
              - Temperature, Light, Greenspace etc. 📍
          - Theory and Methods
            - Multivariate Stochastic Processes (Space & Time)
            - Dynamic Structural Equation Modeling
            - Joint Framework for Mixed-type Data (Ordinal/Binary/Truncated)
            - Graphical Models
          - Applications
            - Mental & Physical Health Dynamics
            - Personalized Prediction 
            - Early Intervention of Mood Disorders
            - Global Mental Health
        </script>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@latest"></script>

  - block: markdown-wide
    id: recent-updates
    content:
      title: News
      text: |
        - **🚨 Looking for motivated students to work on statistical and machine learning methods for analyzing data from wearables ⌚️, smartphones 📱, with contextual location information📍!**
        - 📘 **2026**: Will be teaching **STAT 632: Statistical Methodology II-Bayesian Modeling and Inference** in Spring 2025. 
        - 🎤 **2026**: Will be presenting in the invited session, *Data-driven Advances in Mental Health Statistics: Novel Methods for mHealth, Neuroimaging, and Causal Discovery* at IBC 2026, Seoul, Korea.
        - 📘 **2025**: Will be teaching **STAT 641: The Methods of Statistics I** in Fall 2025. 
        - 🎓 **2025**: Joining **Texas A&M University** as an *Assistant Professor* in the Department of Statistics.

        - 📄 **2025**: Published *Graph-constrained analysis for multivariate functional data* in **Journal of Multivariate Analysis** with S. Banerjee, M. A. Lindquist, and A. Datta.

        - 📄 **2024**: Published *Functional principal component analysis for continuous non-Gaussian, truncated, and discrete functional data* in **Statistics in Medicine** with R. Ghosal, K. Merikangas, and V. Zipunnikov

        - 📰 **2024**: Published *Association Between Electronic Diary–Rated Sleep, Mood, Energy, and Stress With Incident Headache in a Community-Based Sample* in **Neurology** with T. Lateef, A. Leroux, L. Cui, M. Xiao, V. Zipunnikov, and K. Merikangas.  
                      → Featured by: [CNN](https://www.cnn.com/2024/01/24/health/migraine-predict-study-wellness/index.html), [National Geographic](https://www.nationalgeographic.com/premium/article/migraine-prediction-mood-energy-sleep-stress)
        
         - 🎤 **2023**: Organized and chaired a session at **JSM 2023** titled *Recent Developments in Methods for Digital Brain Health Data*.
         - 📰 **2017**: Published *Re-evaluating the effect of age on physical activity over the lifespan* in **Preventive Medicine** with V. Varma, A. Leroux, J. Di, J. Urbanek, L. Xiao, and V. Zipunnikov.  
                        → Featured by: [TIME](https://time.com/4821963/teens-sedentary-lifestyle-exercise/)
---
