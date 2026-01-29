package com.smartrecruit.recruitment.controller;

import com.smartrecruit.recruitment.entity.Candidate;
import com.smartrecruit.recruitment.enums.CandidateStatus;
import com.smartrecruit.recruitment.service.CandidateService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private final CandidateService service;

    public DashboardController(CandidateService service) {
        this.service = service;
    }

    @GetMapping("/pipeline")
    public Map<CandidateStatus, Long> pipelineStats() {
        return service.getPipelineStats();
    }
    @GetMapping("/interviewed")
    public List<Candidate> interviewedCandidates() {
        return service.interviewedCandidates();
    }

}
