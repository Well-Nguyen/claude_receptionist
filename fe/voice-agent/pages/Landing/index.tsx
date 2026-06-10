"use client";

import styles from "./Landing.module.css";

type Props = {
  onLanguageSelect: (lang: "en" | "vi") => void;
};

export default function Landing({ onLanguageSelect }: Props) {
  return (
    <div className={styles.container}>
      <h1 className={styles.title}>
        Chào mừng&nbsp;/&nbsp;Welcome
      </h1>
      <p className={styles.subtitle}>
        Chọn ngôn ngữ&nbsp;·&nbsp;Select language
      </p>
      <div className={styles.buttons}>
        <button
          className={styles.btn}
          onClick={() => onLanguageSelect("vi")}
        >
          Tiếng Việt
        </button>
        <button
          className={styles.btn}
          onClick={() => onLanguageSelect("en")}
        >
          English
        </button>
      </div>
    </div>
  );
}
