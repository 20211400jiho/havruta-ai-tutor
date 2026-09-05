import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import "./CurriculumSelector.css";

function findBy(items, key, value) {
  return items.find((item) => item[key] === value);
}

function makeSelection(catalog, choices = {}, preferredGrade = "") {
  const levels = catalog?.school_levels || [];
  const preferredLevelName = preferredGrade.includes("고등")
    ? "고등학교"
    : preferredGrade.includes("중등") || preferredGrade.includes("중학교")
      ? "중학교"
      : "";
  const level = findBy(levels, "name", choices.schoolLevel)
    || findBy(levels, "name", preferredLevelName)
    || levels[0];
  const grades = level?.grades || [];
  const grade = findBy(grades, "name", choices.grade)
    || grades.find((item) => preferredGrade.includes(item.name))
    || grades[0];
  const units = grade?.units || [];
  const unit = findBy(units, "code", choices.unitCode) || units[0];
  if (!level || !grade || !unit) return null;
  return {
    subject: catalog.name,
    schoolLevel: level.name,
    grade: grade.name,
    unit,
    topic: unit.title,
  };
}

export default function CurriculumSelector({
  subject,
  preferredGrade = "",
  onSelectionChange,
  disabled = false,
  compact = false,
}) {
  const requestKey = `${subject}\u0000${preferredGrade}`;
  const [state, setState] = useState({ key: "", catalog: null, selection: null, error: "" });
  const changeHandlerRef = useRef(onSelectionChange);

  useEffect(() => { changeHandlerRef.current = onSelectionChange; }, [onSelectionChange]);

  const commitSelection = (nextSelection) => {
    setState((current) => ({ ...current, selection: nextSelection }));
    changeHandlerRef.current?.(nextSelection);
  };

  useEffect(() => {
    if (!subject) return undefined;
    let cancelled = false;
    api(`/rag/catalog?subject=${encodeURIComponent(subject)}`)
      .then((result) => {
        if (cancelled) return;
        const nextSelection = makeSelection(result, {}, preferredGrade);
        setState({ key: requestKey, catalog: result, selection: nextSelection, error: "" });
        changeHandlerRef.current?.(nextSelection);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setState({ key: requestKey, catalog: null, selection: null, error: requestError.message });
        changeHandlerRef.current?.(null);
      });
    return () => { cancelled = true; };
  }, [subject, preferredGrade, requestKey]);

  const isCurrent = state.key === requestKey;
  const catalog = isCurrent ? state.catalog : null;
  const selection = isCurrent ? state.selection : null;
  const error = isCurrent ? state.error : "";
  const update = (choices) => commitSelection(makeSelection(catalog, choices, preferredGrade));
  const levels = catalog?.school_levels || [];
  const level = findBy(levels, "name", selection?.schoolLevel);
  const grades = level?.grades || [];
  const grade = findBy(grades, "name", selection?.grade);
  const units = grade?.units || [];

  if (subject && !isCurrent) return <p className="curriculum-state">2022 교육과정 단원을 불러오는 중...</p>;
  if (error) return <p className="curriculum-state error">{error}</p>;
  if (!catalog || !selection) return <p className="curriculum-state">선택 가능한 RAG 단원이 없습니다.</p>;

  return (
    <div className={`curriculum-selector${compact ? " compact" : ""}`}>
      <label>
        학교급
        <select
          aria-label="학교급"
          value={selection.schoolLevel}
          disabled={disabled}
          onChange={(event) => update({ schoolLevel: event.target.value })}
        >
          {levels.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
        </select>
      </label>
      <label>
        학년
        <select
          aria-label="학년"
          value={selection.grade}
          disabled={disabled}
          onChange={(event) => update({ schoolLevel: selection.schoolLevel, grade: event.target.value })}
        >
          {grades.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
        </select>
      </label>
      <label className="curriculum-unit">
        단원
        <select
          aria-label="단원"
          value={selection.unit.code}
          disabled={disabled}
          onChange={(event) => update({
            schoolLevel: selection.schoolLevel,
            grade: selection.grade,
            unitCode: event.target.value,
          })}
        >
          {units.map((item) => (
            <option key={item.code} value={item.code}>
              {item.title} · 자료 {Number(item.document_count ?? 0).toLocaleString()}개
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
