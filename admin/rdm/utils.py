# -*- coding: utf-8 -*-

# ダミーのInstitutionモデルオブジェクトのID
# if文の評価でFalseになることを想定したコードがあるので、
# 0以外の数字にしないこと。
MAGIC_INSTITUTION_ID = 0

class RdmPermissionMixin(object):

    @property
    def is_authenticated(self):
        """ログインしているかどうかを判定する。"""
        return self.request.user.is_authenticated

    @property
    def is_super_admin(self):
        """統合管理者かどうかを判定する。"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # 無効なユーザ
            return False
        if user.is_superuser:
            return True
        return False

    @property
    def is_admin(self):
        """機関管理者かどうか判定する。"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # 無効なユーザ
            return False
        if user.is_staff and not user.is_superuser:
            return True
        return False

    def is_affiliated_institution(self, institution_id):
        """自身が所属する機関か判定する。"""
        user = self.request.user
        if not user.affiliated_institutions.exists():
            if institution_id:
                return False
            return True
        return user.affiliated_institutions.filter(pk=institution_id).exists()

    def has_auth(self, institution_id):
        """機関に対する権限があるかどうか判定する。"""
        # ログインチェック
        if not self.is_authenticated:
            return False
        # 統合管理者なら許可
        if self.is_super_admin:
            return True
        elif self.is_admin:
            return self.is_affiliated_institution(institution_id)
        return False

def get_institution_id(user):
    """ログインユーザが所属するInstitutionのIDを取得する。"""
    if user.affiliated_institutions.exists():
        return user.affiliated_institutions.first().id
    return None

def get_dummy_institution():
    """ユーザがInstitutionに所属していない場合のために、
    ダミーのInstitutionモデルのオブジェクトを取得するする。"""
    class DummyInstitution(object):
        pass
    dummy_institution = DummyInstitution()
    dummy_institution.id = MAGIC_INSTITUTION_ID
    dummy_institution.name = ''
    return dummy_institution
