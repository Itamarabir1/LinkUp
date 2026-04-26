/* View-model bundles refs with state; ref props and handlers are valid in render. */
/* eslint-disable react-hooks/refs -- false positives when vm includes RefObjects */
import { useEffect, useRef } from 'react';
import { Camera, Pencil, Plus, Search, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Group } from '../../types/api';
import type { GroupManageViewModel } from './useGroupManage';
import styles from './GroupManage.module.css';

export interface GroupManageHeaderProps {
  vm: GroupManageViewModel;
  group: Group;
}

export default function GroupManageHeader({ vm, group }: GroupManageHeaderProps) {
  const { t } = useTranslation(['groups', 'common']);
  const { groupId, navigate, isAdmin } = vm;
  const nameInputRef = useRef<HTMLInputElement>(null);
  const descTextareaRef = useRef<HTMLTextAreaElement>(null);
  const memberCount = group.member_count ?? vm.members.length;

  useEffect(() => {
    if (vm.isEditingName) {
      nameInputRef.current?.focus();
    }
  }, [vm.isEditingName]);

  useEffect(() => {
    if (vm.isEditingDesc) {
      descTextareaRef.current?.focus();
    }
  }, [vm.isEditingDesc]);

  return (
    <header className={styles.groupHeader}>
      {isAdmin && (
        <button
          type="button"
          className={styles.headerSettingsBtn}
          onClick={() => vm.setActiveTab('settings')}
          title={t('groups:groupSettingsTitle')}
        >
          <Settings size={18} />
        </button>
      )}

      <input
        ref={vm.headerFileInputRef}
        type="file"
        accept="image/*"
        className={styles.hiddenInput}
        onChange={vm.handleHeaderImageChange}
      />

      <button
        type="button"
        className={styles.headerAvatarWrap}
        onClick={vm.handleAvatarClick}
        disabled={vm.headerSaving || !isAdmin}
      >
        {group.avatar_url && !vm.headerPreviewUrl ? (
          <img
            src={group.avatar_url}
            alt={group.name}
            className={styles.headerAvatarImg}
            loading="eager"
            fetchPriority="high"
          />
        ) : vm.headerPreviewUrl ? (
          <img
            src={vm.headerPreviewUrl}
            alt={group.name}
            className={styles.headerAvatarImg}
            loading="eager"
            fetchPriority="high"
          />
        ) : (
          <div
            className={styles.headerAvatar}
            style={{ ['--avatar-bg' as string]: vm.groupAvatarColor }}
          >
            {group.name.charAt(0).toUpperCase()}
          </div>
        )}
        {isAdmin && (
          <span className={styles.headerAvatarOverlay}>
            <Camera size={20} />
          </span>
        )}
      </button>

      {!vm.isEditingName ? (
        <div className={styles.nameRow}>
          <h1 className={styles.headerName}>{group.name}</h1>
          {isAdmin && (
            <button
              type="button"
              className={styles.editIconBtn}
              onClick={() => vm.setIsEditingName(true)}
              aria-label={t('groups:editGroupNameAria')}
            >
              <Pencil size={14} />
            </button>
          )}
        </div>
      ) : (
        <div className={styles.inlineEditRow}>
          <input
            ref={nameInputRef}
            type="text"
            className={styles.inlineInput}
            value={vm.editNameValue}
            onChange={(e) => vm.setEditNameValue(e.target.value)}
            maxLength={50}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                void vm.handleNameSave();
              }
              if (e.key === 'Escape') {
                vm.setEditNameValue(group.name);
                vm.setIsEditingName(false);
              }
            }}
            disabled={vm.headerSaving}
          />
          <button
            type="button"
            className={styles.inlineSave}
            onClick={() => void vm.handleNameSave()}
            disabled={vm.headerSaving}
          >
            ✓
          </button>
          <button
            type="button"
            className={styles.inlineCancel}
            onClick={() => {
              vm.setEditNameValue(group.name);
              vm.setIsEditingName(false);
            }}
            disabled={vm.headerSaving}
          >
            ✕
          </button>
        </div>
      )}

      {!vm.isEditingDesc ? (
        <div className={styles.descRow}>
          <p className={styles.headerDescription}>
            {group.description || (isAdmin ? t('groups:addDescriptionPlaceholder') : '')}
          </p>
          {isAdmin && (
            <button
              type="button"
              className={styles.editIconBtn}
              onClick={() => vm.setIsEditingDesc(true)}
              aria-label={t('groups:editGroupDescriptionAria')}
            >
              <Pencil size={14} />
            </button>
          )}
        </div>
      ) : (
        <div className={styles.inlineEditCol}>
          <textarea
            ref={descTextareaRef}
            className={styles.inlineTextarea}
            value={vm.editDescriptionValue}
            onChange={(e) => vm.setEditDescriptionValue(e.target.value.slice(0, 500))}
            rows={2}
            disabled={vm.headerSaving}
          />
          <div className={styles.inlineActions}>
            <button
              type="button"
              className={styles.inlineSave}
              onClick={() => void vm.handleDescSave()}
              disabled={vm.headerSaving}
            >
              {t('common:save')}
            </button>
            <button
              type="button"
              className={styles.inlineCancel}
              onClick={() => {
                vm.setEditDescriptionValue(group.description ?? '');
                vm.setIsEditingDesc(false);
              }}
              disabled={vm.headerSaving}
            >
              {t('common:cancel')}
            </button>
          </div>
        </div>
      )}

      <p className={styles.groupMeta}>
        👥 {t('groups:membersLabel', { count: memberCount })}
        {group.is_active === false && t('groups:groupInactiveSuffix')}
      </p>

      <div className={styles.headerActions}>
        <button
          type="button"
          className={styles.headerBtn}
          onClick={() => navigate(`/groups/${groupId}/rides/search`)}
          title={t('groups:searchRideInGroupTitle')}
        >
          <Search size={18} />
          {t('groups:searchRideInGroup')}
        </button>
        <button
          type="button"
          className={styles.headerBtnPrimary}
          onClick={() => navigate(`/groups/${groupId}/rides/create`)}
          title={t('groups:offerRideToGroupTitle')}
        >
          <Plus size={18} />
          {t('groups:offerRideToGroup')}
        </button>
      </div>
    </header>
  );
}
