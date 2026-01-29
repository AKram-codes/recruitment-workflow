package com.smartrecruit.recruitment.controller;

import com.smartrecruit.recruitment.entity.Assessment;
import com.smartrecruit.recruitment.service.AssessmentService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/assessments")
public class AssessmentController {

    private final AssessmentService service;

    public AssessmentController(AssessmentService service) {
        this.service = service;
    }

    @PostMapping
    public Assessment assessCandidate(
            @RequestParam Long candidateId,
            @RequestParam int technicalScore,
            @RequestParam int communicationScore) {

        return service.assessCandidate(candidateId, technicalScore, communicationScore);
    }
    @PostMapping("/decision")
    public String autoDecision(@RequestParam Long candidateId) {
        return service.autoDecide(candidateId);
    }

}
