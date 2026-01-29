package com.smartrecruit.recruitment.controller;

import com.smartrecruit.recruitment.entity.Candidate;
import com.smartrecruit.recruitment.enums.CandidateStatus;
import com.smartrecruit.recruitment.service.CandidateService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/candidates")
public class CandidateController {

    private final CandidateService service;

    public CandidateController(CandidateService service) {
        this.service = service;
    }

    @PostMapping
    public Candidate create(@RequestBody Candidate candidate) {
        return service.createCandidate(candidate);
    }

    @PatchMapping("/{id}/status")
    public Candidate updateStatus(
            @PathVariable Long id,
            @RequestParam CandidateStatus status) {

        return service.updateStatus(id, status);
    }

    @GetMapping
    public List<Candidate> byStatus(@RequestParam CandidateStatus status) {
        return service.getByStatus(status);
    }
}
