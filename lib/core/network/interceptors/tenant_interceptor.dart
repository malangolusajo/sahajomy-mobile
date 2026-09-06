import 'package:dio/dio.dart';

import '../../workspaces/workspace_provider.dart';

class TenantInterceptor extends Interceptor {
  TenantInterceptor(this._workspaceProvider);

  final WorkspaceProvider _workspaceProvider;

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final skipTenant = options.extra['skipTenant'] == true;
    if (skipTenant) {
      handler.next(options);
      return;
    }

    options.extra['tenantRevision'] = _workspaceProvider.revision;

    final companyId = _workspaceProvider.currentCompanyId;
    final branchId = _workspaceProvider.currentBranchId;

    if (companyId != null && companyId.isNotEmpty) {
      options.headers['X-Sahajomy-Company'] = companyId;
    }
    if (branchId != null && branchId.isNotEmpty) {
      options.headers['X-Sahajomy-Branch'] = branchId;
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    final requestRevision = response.requestOptions.extra['tenantRevision'];
    if (requestRevision != null &&
        requestRevision != _workspaceProvider.revision) {
      handler.reject(
        DioException(
          requestOptions: response.requestOptions,
          response: response,
          type: DioExceptionType.cancel,
          message: 'Tenant context changed before the response completed.',
        ),
      );
      return;
    }
    handler.next(response);
  }
}
