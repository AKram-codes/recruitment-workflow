package com.smartrecruit.recruitment.config;

import com.smartrecruit.recruitment.entity.User;
import com.smartrecruit.recruitment.enums.UserRole;
import com.smartrecruit.recruitment.repository.UserRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
public class DataLoader {

    @Bean
    CommandLineRunner loadUsers(UserRepository repo, PasswordEncoder encoder) {
        return args -> {
            if (repo.count() == 0) {

                User admin = new User();
                admin.setUsername("admin");
                admin.setPassword(encoder.encode("admin123"));
                admin.setRole(UserRole.ADMIN);

                User recruiter = new User();
                recruiter.setUsername("recruiter");
                recruiter.setPassword(encoder.encode("recruiter123"));
                recruiter.setRole(UserRole.RECRUITER);

                repo.save(admin);
                repo.save(recruiter);
            }
        };
    }
}
