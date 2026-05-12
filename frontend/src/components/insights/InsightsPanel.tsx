import { useInsights } from '../../api/queries';
import SkeletonRow from '../SkeletonRow';
import styles from './InsightsPanel.module.css';

export function InsightsPanel() {
  const { data, isLoading, isError } = useInsights();

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.tag}>Insights</span>
        <h2 className={styles.title}>Key Findings</h2>
      </div>

      {isLoading && (
        <div className={styles.list}>
          {[1, 2, 3].map(i => <SkeletonRow key={i} />)}
        </div>
      )}

      {isError && (
        <p className={styles.empty}>Could not load insights.</p>
      )}

      {data && (
        <ul className={styles.list}>
          {data.findings.map(f => (
            <li
              key={f.id}
              className={`${styles.card} ${
                f.polarity === 'positive'
                  ? styles.positive
                  : f.polarity === 'negative'
                  ? styles.negative
                  : ''
              }`}
            >
              <p
                className={styles.text}
                dangerouslySetInnerHTML={{ __html: f.text }}
              />
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}