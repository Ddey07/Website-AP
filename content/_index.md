---
# Leave the homepage title empty to use the site title
title: ""
date: 2022-10-24
type: landing

design:
  # Default section spacing
  spacing: "6rem"

sections:
  - block: resume-biography-4
    content:
      # Choose a user profile to display (a folder name within `content/authors/`)
      username: admin
      text: ""
      # Show a call-to-action button under your biography? (optional)
      button:
        text: Download CV
        url: uploads/resume.pdf
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
    id: recent-updates
    content:
      title: News
      text: |
        - 📘 **2025**: Will be teaching **STAT 641: The Methods of Statistics I** in Fall 2025. 
        - 🎓 **2025**: Joining **Texas A&M University** as an *Assistant Professor* in the Department of Statistics.

        - 📄 **2025**: Published *Graph-constrained analysis for multivariate functional data* in *Journal of Multivariate Analysis* with S. Banerjee, M. A. Lindquist, and A. Datta.

        - 📄 **2024**: Published *Functional principal component analysis for continuous non-Gaussian, truncated, and discrete functional data* in *Statistics in Medicine* with R. Ghosal, K. Merikangas, and V. Zipunnikov.

        - 📰 **2024**: Published *Association Between Electronic Diary–Rated Sleep, Mood, Energy, and Stress With Incident Headache in a Community-Based Sample* in *Neurology* with T. Lateef, A. Leroux, L. Cui, M. Xiao, V. Zipunnikov, and K. Merikangas.  
                      → Featured by: [CNN](https://www.cnn.com/2024/01/24/health/migraine-predict-study-wellness/index.html), [National Geographic](https://www.nationalgeographic.com/premium/article/migraine-prediction-mood-energy-sleep-stress), [NIH Director’s Blog](https://directorsblog.nih.gov/2024/01/25/monitoring-mood-sleep-and-energy-to-help-predict-migraines/)
        
         -  🎤 **2023**: Organized and chaired a session at **JSM 2023** titled *Recent Developments in Methods for Digital Brain Health Data*.
         - 📰 **2017**: Published *Re-evaluating the effect of age on physical activity over the lifespan* in *Preventive Medicine* with V. Varma, A. Leroux, J. Di, J. Urbanek, L. Xiao, and V. Zipunnikov.  
                        → Featured by: [TIME](https://time.com/4821963/teens-sedentary-lifestyle-exercise/), [Washington Post](https://www.washingtonpost.com/news/to-your-health/wp/2017/06/15/teens-are-as-sedentary-as-60-year-olds-study-finds/), [BBC](https://www.bbc.com/news/health-40210738), [WSJ](https://www.wsj.com/articles/sedentary-teens-as-inactive-as-seniors-study-says-1497452400)

---