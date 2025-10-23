import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('../Data/건축물대장_v0.5.csv')
df.columns
df.info()

# 종합점수 시각화
plt.figure(figsize=(10, 6))
sns.histplot(df["종합점수"], kde=False, bins=50, color="skyblue")
plt.title("종합점수 분포", fontsize=16)
plt.xlabel("종합점수", fontsize=12)
plt.ylabel("건물 수", fontsize=12)
plt.show()