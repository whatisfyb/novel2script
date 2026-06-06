package com.novel.history.interfaces.rest;

import com.novel.history.application.service.HistoryAppService;
import com.novel.history.common.result.R;
import com.novel.history.interfaces.rest.dto.CreateHistoryRequest;
import com.novel.history.interfaces.rest.dto.HistoryListResponse;
import com.novel.history.interfaces.rest.dto.HistoryResponse;
import com.novel.history.interfaces.rest.dto.UpdateHistoryRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

/**
 * History REST controller — handles /api/history endpoints.
 */
@RestController
@RequestMapping("/api/history")
public class HistoryController {

    private final HistoryAppService historyAppService;

    public HistoryController(HistoryAppService historyAppService) {
        this.historyAppService = historyAppService;
    }

    @PostMapping
    public R<HistoryResponse> create(@Valid @RequestBody CreateHistoryRequest request) {
        HistoryResponse response = historyAppService.create(request);
        return R.ok(response);
    }

    @GetMapping("/{runId}")
    public R<HistoryResponse> getByRunId(@PathVariable String runId) {
        HistoryResponse response = historyAppService.getByRunId(runId);
        return R.ok(response);
    }

    @GetMapping
    public R<HistoryListResponse> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String scriptType,
            @RequestParam(required = false) String status) {
        HistoryListResponse response = historyAppService.list(page, size, scriptType, status);
        return R.ok(response);
    }

    @PatchMapping("/{runId}")
    public R<HistoryResponse> update(
            @PathVariable String runId,
            @Valid @RequestBody UpdateHistoryRequest request) {
        HistoryResponse response = historyAppService.update(runId, request);
        return R.ok(response);
    }

    @DeleteMapping("/{runId}")
    public R<Void> delete(@PathVariable String runId) {
        historyAppService.delete(runId);
        return R.ok();
    }
}
