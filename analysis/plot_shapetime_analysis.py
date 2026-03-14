#!/usr/bin/env python3
"""
Plotting script for analyzing ShapeTime metric results.

Creates visualizations for the ShapeTime comparison between 
Raag Bhairav and Turkish Makams.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def load_data(data_dir: Path) -> Dict[str, pd.DataFrame]:
    """Load all ShapeTime CSV files."""
    data = {}
    
    pairwise_path = data_dir / 'shapetime_pairwise.csv'
    if pairwise_path.exists():
        data['pairwise'] = pd.read_csv(pairwise_path)
    
    by_makam_path = data_dir / 'shapetime_by_makam.csv'
    if by_makam_path.exists():
        data['by_makam'] = pd.read_csv(by_makam_path)
    
    by_makam_only_path = data_dir / 'shapetime_by_makam_only.csv'
    if by_makam_only_path.exists():
        data['by_makam_only'] = pd.read_csv(by_makam_only_path)
    
    return data


def plot_top_makams_bar(df: pd.DataFrame, output_dir: Path, top_n: int = 15):
    """Bar chart of top N makams most similar to Bhairav."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # By average rank (lower is better)
    df_sorted = df.nsmallest(top_n, 'avg_rank')
    
    ax = axes[0]
    colors = sns.color_palette("viridis", n_colors=top_n)
    bars = ax.barh(range(top_n), df_sorted['avg_rank'], color=colors)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(df_sorted['makam'])
    ax.invert_yaxis()
    ax.set_xlabel('Average ShapeTime Rank (lower = more similar)')
    ax.set_title('Top Makams by ShapeTime Ranking')
    
    # Add rank values on bars
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax.text(row['avg_rank'] + 0.5, i, f"{row['avg_rank']:.1f}", 
                va='center', fontsize=9)
    
    # By ShapeH mean score (higher is better)
    df_sorted = df.nlargest(top_n, 'shapeh_mean')
    
    ax = axes[1]
    bars = ax.barh(range(top_n), df_sorted['shapeh_mean'], color=colors)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(df_sorted['makam'])
    ax.invert_yaxis()
    ax.set_xlabel('Mean ShapeH Score (higher = more similar)')
    ax.set_title('Top Makams by ShapeH Similarity')
    
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax.text(row['shapeh_mean'] + 0.1, i, f"{row['shapeh_mean']:.2f}", 
                va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'top_makams_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'top_makams_comparison.png'}")


def plot_shapeh_vs_time(df: pd.DataFrame, output_dir: Path):
    """Scatter plot comparing ShapeH and Time scores."""
    # Filter to records with both scores
    df_valid = df[df['time_score'].notna()].copy()
    
    if df_valid.empty:
        print("Warning: No records with both ShapeH and Time scores")
        return
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Get unique makams for coloring
    unique_makams = df_valid['makam'].unique()
    n_makams = len(unique_makams)
    
    if n_makams <= 20:
        colors = sns.color_palette("husl", n_colors=n_makams)
        makam_colors = {m: colors[i] for i, m in enumerate(unique_makams)}
        
        for makam in unique_makams:
            mask = df_valid['makam'] == makam
            ax.scatter(
                df_valid.loc[mask, 'shapeh_score'],
                df_valid.loc[mask, 'time_score'],
                label=makam,
                alpha=0.7,
                s=50
            )
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    else:
        scatter = ax.scatter(
            df_valid['shapeh_score'],
            df_valid['time_score'],
            c=df_valid['shapetime_rank'],
            cmap='viridis_r',
            alpha=0.6,
            s=50
        )
        plt.colorbar(scatter, ax=ax, label='ShapeTime Rank')
    
    ax.set_xlabel('ShapeH Score')
    ax.set_ylabel('Time Score')
    ax.set_title('ShapeH vs Time Score (Top-k pairs only)')
    
    # Add correlation
    corr = df_valid['shapeh_score'].corr(df_valid['time_score'])
    ax.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
            transform=ax.transAxes, fontsize=11, va='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'shapeh_vs_time_scatter.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'shapeh_vs_time_scatter.png'}")


def plot_rank_distribution(df: pd.DataFrame, output_dir: Path, top_n: int = 10):
    """Box plot showing rank distribution for top makams."""
    # Get top makams by mean rank
    top_makams = df.groupby('makam')['shapetime_rank'].mean().nsmallest(top_n).index.tolist()
    
    df_filtered = df[df['makam'].isin(top_makams)].copy()
    
    # Order by mean rank
    order = df_filtered.groupby('makam')['shapetime_rank'].mean().sort_values().index.tolist()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    sns.boxplot(
        data=df_filtered,
        x='makam',
        y='shapetime_rank',
        order=order,
        palette='viridis',
        ax=ax
    )
    
    ax.set_xlabel('Makam')
    ax.set_ylabel('ShapeTime Rank')
    ax.set_title(f'Rank Distribution for Top {top_n} Makams')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'rank_distribution_boxplot.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'rank_distribution_boxplot.png'}")


def plot_heatmap_by_usul(df: pd.DataFrame, output_dir: Path, top_n: int = 15):
    """Heatmap showing similarity by makam and usul."""
    # Pivot to create makam x usul matrix
    pivot = df.pivot_table(
        values='shapeh_mean',
        index='makam',
        columns='usul',
        aggfunc='mean'
    )
    
    # Keep top makams by overall mean
    top_makams = df.groupby('makam')['shapeh_mean'].mean().nlargest(top_n).index.tolist()
    pivot = pivot.loc[pivot.index.isin(top_makams)]
    
    # Keep usuls with enough data
    usul_counts = df.groupby('usul').size()
    frequent_usuls = usul_counts[usul_counts >= 5].index.tolist()
    pivot = pivot[[c for c in pivot.columns if c in frequent_usuls]]
    
    if pivot.empty or pivot.shape[1] < 2:
        print("Warning: Not enough data for usul heatmap")
        return
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    sns.heatmap(
        pivot,
        cmap='YlOrRd',
        annot=True,
        fmt='.2f',
        ax=ax,
        cbar_kws={'label': 'Mean ShapeH Score'}
    )
    
    ax.set_xlabel('Usul')
    ax.set_ylabel('Makam')
    ax.set_title('ShapeH Similarity: Makam × Usul')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'makam_usul_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'makam_usul_heatmap.png'}")


def plot_score_histogram(df: pd.DataFrame, output_dir: Path):
    """Histogram of ShapeH and Time scores."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # ShapeH distribution
    ax = axes[0]
    ax.hist(df['shapeh_score'], bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(df['shapeh_score'].mean(), color='red', linestyle='--', 
               label=f'Mean: {df["shapeh_score"].mean():.2f}')
    ax.axvline(df['shapeh_score'].median(), color='orange', linestyle='--', 
               label=f'Median: {df["shapeh_score"].median():.2f}')
    ax.set_xlabel('ShapeH Score')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of ShapeH Scores')
    ax.legend()
    
    # Time score distribution (only for top-k)
    ax = axes[1]
    time_scores = df['time_score'].dropna()
    if not time_scores.empty:
        ax.hist(time_scores, bins=30, color='coral', alpha=0.7, edgecolor='black')
        ax.axvline(time_scores.mean(), color='red', linestyle='--', 
                   label=f'Mean: {time_scores.mean():.2f}')
        ax.axvline(time_scores.median(), color='orange', linestyle='--', 
                   label=f'Median: {time_scores.median():.2f}')
        ax.set_xlabel('Time Score')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of Time Scores (Top-k only)')
        ax.legend()
    else:
        ax.text(0.5, 0.5, 'No Time scores available', ha='center', va='center',
                transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'score_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'score_distributions.png'}")


def plot_top_k_analysis(df: pd.DataFrame, output_dir: Path):
    """Analyze which makams frequently appear in top-k."""
    by_makam = df.groupby('makam').agg({
        'time_score': lambda x: x.notna().sum(),  # Count of top-k appearances
        'shapetime_rank': 'mean',
        'shapeh_score': 'mean'
    }).reset_index()
    
    by_makam.columns = ['makam', 'top_k_count', 'avg_rank', 'shapeh_mean']
    by_makam = by_makam.nlargest(15, 'top_k_count')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = sns.color_palette("viridis", n_colors=len(by_makam))
    bars = ax.bar(range(len(by_makam)), by_makam['top_k_count'], color=colors)
    ax.set_xticks(range(len(by_makam)))
    ax.set_xticklabels(by_makam['makam'], rotation=45, ha='right')
    ax.set_xlabel('Makam')
    ax.set_ylabel('Number of Top-k Appearances')
    ax.set_title('Makams Most Frequently in Top-k Similar to Bhairav')
    
    # Add count labels
    for i, (idx, row) in enumerate(by_makam.iterrows()):
        ax.text(i, row['top_k_count'] + 0.5, str(int(row['top_k_count'])), 
                ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'topk_frequency.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'topk_frequency.png'}")


def plot_summary_dashboard(df_pairwise: pd.DataFrame, df_makam: pd.DataFrame, 
                           output_dir: Path):
    """Create a summary dashboard with multiple metrics."""
    fig = plt.figure(figsize=(16, 12))
    
    # Top 10 by rank
    ax1 = fig.add_subplot(2, 2, 1)
    top10 = df_makam.nsmallest(10, 'avg_rank')
    colors = plt.cm.viridis(np.linspace(0, 0.8, 10))
    bars = ax1.barh(range(10), top10['avg_rank'], color=colors)
    ax1.set_yticks(range(10))
    ax1.set_yticklabels(top10['makam'])
    ax1.invert_yaxis()
    ax1.set_xlabel('Average Rank')
    ax1.set_title('Top 10 Makams (by Rank)')
    for i, v in enumerate(top10['avg_rank']):
        ax1.text(v + 0.3, i, f'{v:.1f}', va='center', fontsize=9)
    
    # Score distribution
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.hist(df_pairwise['shapeh_score'], bins=40, color='steelblue', 
             alpha=0.7, edgecolor='black')
    ax2.axvline(df_pairwise['shapeh_score'].mean(), color='red', linestyle='--', lw=2)
    ax2.set_xlabel('ShapeH Score')
    ax2.set_ylabel('Frequency')
    ax2.set_title('ShapeH Score Distribution')
    
    # Top 10 by ShapeH score
    ax3 = fig.add_subplot(2, 2, 3)
    top10_shapeh = df_makam.nlargest(10, 'shapeh_mean')
    colors = plt.cm.plasma(np.linspace(0, 0.8, 10))
    bars = ax3.barh(range(10), top10_shapeh['shapeh_mean'], color=colors)
    ax3.set_yticks(range(10))
    ax3.set_yticklabels(top10_shapeh['makam'])
    ax3.invert_yaxis()
    ax3.set_xlabel('Mean ShapeH Score')
    ax3.set_title('Top 10 Makams (by ShapeH)')
    for i, v in enumerate(top10_shapeh['shapeh_mean']):
        ax3.text(v + 0.05, i, f'{v:.2f}', va='center', fontsize=9)
    
    # Stats summary
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    
    stats_text = f"""
    SHAPETIME ANALYSIS SUMMARY
    ═══════════════════════════════════════
    
    Dataset Statistics:
    • Total pairwise comparisons: {len(df_pairwise):,}
    • Unique makams compared: {df_pairwise['makam'].nunique()}
    • Unique usuls: {df_pairwise['usul'].nunique()}
    • Bhairav melodies analyzed: {df_pairwise['raga_file'].nunique()}
    
    Score Statistics:
    • ShapeH mean: {df_pairwise['shapeh_score'].mean():.3f}
    • ShapeH std: {df_pairwise['shapeh_score'].std():.3f}
    • ShapeH range: [{df_pairwise['shapeh_score'].min():.3f}, {df_pairwise['shapeh_score'].max():.3f}]
    
    Top Similar Makams to Bhairav:
    1. {df_makam.nsmallest(5, 'avg_rank').iloc[0]['makam']}
    2. {df_makam.nsmallest(5, 'avg_rank').iloc[1]['makam']}
    3. {df_makam.nsmallest(5, 'avg_rank').iloc[2]['makam']}
    4. {df_makam.nsmallest(5, 'avg_rank').iloc[3]['makam']}
    5. {df_makam.nsmallest(5, 'avg_rank').iloc[4]['makam']}
    """
    
    ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))
    
    plt.suptitle('Raag Bhairav vs Turkish Makams: ShapeTime Analysis', 
                 fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_dir / 'shapetime_dashboard.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'shapetime_dashboard.png'}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate plots for ShapeTime analysis'
    )
    parser.add_argument('--data-dir', default='analysis/output/shapetime',
                        help='Directory containing ShapeTime CSV files')
    parser.add_argument('--output-dir', default='analysis/output/shapetime/plots',
                        help='Output directory for plots')
    parser.add_argument('--top-n', type=int, default=15,
                        help='Number of top results to show in plots')
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {data_dir}")
    data = load_data(data_dir)

    if not data:
        print("ERROR: No data files found! Run run_shapetime_bhairav.py first.")
        sys.exit(1)

    print(f"Loaded: {list(data.keys())}")

    # Generate plots
    if 'pairwise' in data:
        print("\nGenerating score histogram...")
        plot_score_histogram(data['pairwise'], output_dir)
        
        print("Generating ShapeH vs Time scatter...")
        plot_shapeh_vs_time(data['pairwise'], output_dir)
        
        print("Generating rank distribution...")
        plot_rank_distribution(data['pairwise'], output_dir, top_n=args.top_n)
        
        print("Generating top-k analysis...")
        plot_top_k_analysis(data['pairwise'], output_dir)

    if 'by_makam' in data:
        print("Generating heatmap by usul...")
        plot_heatmap_by_usul(data['by_makam'], output_dir, top_n=args.top_n)

    if 'by_makam_only' in data:
        print("Generating top makams bar chart...")
        plot_top_makams_bar(data['by_makam_only'], output_dir, top_n=args.top_n)

    if 'pairwise' in data and 'by_makam_only' in data:
        print("Generating summary dashboard...")
        plot_summary_dashboard(data['pairwise'], data['by_makam_only'], output_dir)

    print(f"\nAll plots saved to: {output_dir}")
    print("Done!")


if __name__ == '__main__':
    main()
