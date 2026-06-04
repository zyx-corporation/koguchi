class EnvelopeRequiredError(Exception):
    """ActionEnvelope を伴わない管理対象副作用が実行されようとした。"""


class StoreWriteError(Exception):
    """ExecutionStore への書き込みに失敗した。"""


class WorkspaceBoundaryError(Exception):
    """操作対象が workspace_dir の外にある。"""
